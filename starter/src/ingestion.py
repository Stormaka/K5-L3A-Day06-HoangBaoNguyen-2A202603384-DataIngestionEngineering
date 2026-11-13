"""Read and normalize source data: PDF page extraction, Unicode/whitespace
normalization and paragraph segmentation, with per-page error logging."""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

from pypdf import PdfReader

from .models import DocumentPage

# Lines shorter than this fraction of a page's median line length end a
# paragraph (headings, list items and title lines in these reports are short).
_SHORT_LINE_RATIO = 0.62


def normalize_text(text: str) -> str:
    """Normalize Unicode (NFC), fold ligatures, de-hyphenate line breaks and
    collapse whitespace while keeping line/paragraph structure."""
    text = unicodedata.normalize("NFC", text)
    for src, dst in (
        ("\ufb00", "ff"), ("\ufb01", "fi"), ("\ufb02", "fl"),
        ("\ufb03", "ffi"), ("\ufb04", "ffl"), ("\u00a0", " "),
        ("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'), ("\u201d", '"'),
    ):
        text = text.replace(src, dst)
    lines = [line.strip() for line in text.split("\n")]
    # Collapse runs of spaces/tabs inside lines (word wrap joins and
    # de-hyphenation happen later, in paragraphs()).
    return "\n".join(" ".join(line.split()) for line in lines).strip("\n")


def paragraphs(text: str) -> list[str]:
    """Segment normalized page text into paragraphs.

    Joins wrapped source lines into one paragraph until a short line (a
    heading, bullet or title line) signals a boundary; removes soft-hyphen
    line breaks while joining. Deterministic and locale-independent.
    """
    lines = [line for line in text.split("\n")]
    lengths = [len(line) for line in lines if line.strip()]
    if not lengths:
        return []
    lengths.sort()
    median = lengths[len(lengths) // 2] or 1

    paras: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        joined = ""
        for piece in current:
            if joined.endswith("-"):
                joined = joined[:-1] + piece
            else:
                joined = (joined + " " + piece) if joined else piece
        joined = " ".join(joined.split())
        if joined:
            paras.append(joined)
        current.clear()

    for line in lines:
        if not line.strip():
            flush()
            continue
        is_boundary = len(line) < max(median * _SHORT_LINE_RATIO, 20)
        if is_boundary and current:
            flush()
            current.append(line)
            flush()
        else:
            current.append(line)
    flush()
    return paras


def load_pdf(path: Path, document_id: str, source: str,
             metadata: dict | None = None) -> tuple[list[DocumentPage], list[dict]]:
    """Extract each physical page of a PDF into a DocumentPage.

    Physical page numbers are 1-based and used as traceable page IDs.
    Returns (pages, issues) where issues records empty/failed pages; pages
    with no extractable text are kept out of the chunking input.
    """
    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []
    issues: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception as exc:  # extraction failures are recorded, not hidden
            issues.append({"document_id": document_id, "page": index,
                           "issue": f"extract_error: {type(exc).__name__}"})
            raw = ""
        text = normalize_text(raw)
        if not text or len(text.strip()) < 10:
            issues.append({"document_id": document_id, "page": index,
                           "issue": "no_text"})
            continue
        page_meta = dict(metadata or {})
        page_meta["chars"] = len(text)
        pages.append(DocumentPage(document_id=document_id, source=source,
                                  page=index, text=text, metadata=page_meta))
    if issues:
        dump = Path(__file__).resolve().parents[2] / "results" / "extraction_issues.json"
        dump.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(dump.read_text(encoding="utf-8")) if dump.exists() else []
        existing = [i for i in existing if i["document_id"] != document_id]
        existing.extend(issues)
        dump.write_text(json.dumps(existing, indent=2, ensure_ascii=False),
                        encoding="utf-8")
    return pages, issues
