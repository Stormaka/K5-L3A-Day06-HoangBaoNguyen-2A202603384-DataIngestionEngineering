"""Fixed-size and structure-aware chunking.

Both strategies chunk within a single page so that page metadata stays an
exact trace, never an approximation across page boundaries.
"""
from __future__ import annotations

import hashlib
import re

from .ingestion import paragraphs
from .models import Chunk, DocumentPage

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


def _mk_chunk(page: DocumentPage, text: str, index: int, extra: dict) -> Chunk:
    digest = hashlib.sha1(
        f"{page.document_id}|{page.page}|{index}|{text[:80]}".encode("utf-8")
    ).hexdigest()[:10]
    meta = dict(page.metadata)
    meta.update(extra)
    return Chunk(
        chunk_id=f"{page.document_id}:p{page.page}:c{index}:{digest}",
        document_id=page.document_id,
        source=page.source,
        page=page.page,
        text=text,
        metadata=meta,
    )


def _page_text(page: DocumentPage) -> str:
    """Full page as one whitespace-joined block (for fixed-size windows)."""
    return " ".join(" ".join(page.text.split("\n")).split())


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Sliding character windows of `size` with `overlap`, page-local."""
    text = _page_text(page)
    if not text:
        return []
    chunks: list[Chunk] = []
    step = max(size - overlap, 1)
    index = 0
    start = 0
    while start < len(text):
        window = text[start:start + size]
        chunks.append(_mk_chunk(
            page, window, index,
            {"strategy_chunker": "fixed", "size": size, "overlap": overlap},
        ))
        index += 1
        if start + size >= len(text):
            break
        start += step
    return chunks


def _split_long(paragraph: str, max_size: int) -> list[str]:
    """Split one oversized paragraph at sentence boundaries under max_size."""
    if len(paragraph) <= max_size:
        return [paragraph]
    sentences = _SENTENCE_SPLIT.split(paragraph)
    parts: list[str] = []
    buf = ""
    for sentence in sentences:
        candidate = (buf + " " + sentence).strip() if buf else sentence
        if len(candidate) > max_size and buf:
            parts.append(buf)
            buf = sentence
        else:
            buf = candidate
        while len(buf) > max_size:  # pathological single long "sentence"
            parts.append(buf[:max_size])
            buf = buf[max_size:]
    if buf:
        parts.append(buf)
    return parts


def _is_heading(paragraph: str) -> bool:
    """Short line without terminal punctuation acts as a section heading."""
    return (len(paragraph) <= 90
            and not paragraph.rstrip().endswith((".", ":", "!", "?", ";", ","))
            and not paragraph.startswith(("•", "-", "–")))


def by_paragraph(page: DocumentPage, max_size: int = 1000,
                 merge_min: int = 150) -> list[Chunk]:
    """Structure-aware chunks: group paragraphs under a shared heading,
    merge short neighbours, split oversized paragraphs on sentences."""
    paras = paragraphs(page.text)
    if not paras:
        return []

    # Attach a heading to the block that follows it as context prefix.
    blocks: list[tuple[str | None, list[str]]] = []
    for para in paras:
        if _is_heading(para) and not blocks:
            blocks.append((para, []))
        elif _is_heading(para):
            blocks.append((para, []))
        elif blocks:
            blocks[-1][1].append(para)
        else:
            blocks.append((None, [para]))
    blocks = [(h, ps) for h, ps in blocks if ps or h]

    chunks: list[Chunk] = []
    index = 0
    buf: list[str] = []
    heading: str | None = None

    def flush() -> None:
        nonlocal buf, index, heading
        if not buf:
            heading = None
            return
        body = " ".join(buf)
        prefix = f"{heading}. " if heading else ""
        for part in _split_long(body, max_size - len(prefix)):
            chunks.append(_mk_chunk(
                page, prefix + part, index,
                {"strategy_chunker": "paragraph", "max_size": max_size,
                 "heading": heading or ""},
            ))
            index += 1
        buf = []
        heading = None

    for head, paras_in_block in blocks:
        for para in paras_in_block:
            for piece in _split_long(para, max_size):
                if buf and len(" ".join(buf)) + len(piece) + 1 > max_size:
                    flush()
                if not buf:
                    heading = head
                buf.append(piece)
                if len(" ".join(buf)) >= max_size:
                    flush()
    flush()

    # Merge tiny trailing chunks into their predecessor when possible.
    merged: list[Chunk] = []
    for chunk in chunks:
        if (merged and len(chunk.text) < merge_min
                and len(merged[-1].text) + len(chunk.text) + 1 <= max_size + 200):
            merged[-1] = Chunk(
                chunk_id=merged[-1].chunk_id, document_id=merged[-1].document_id,
                source=merged[-1].source, page=merged[-1].page,
                text=merged[-1].text + " " + chunk.text,
                metadata=merged[-1].metadata,
            )
        else:
            merged.append(chunk)
    return merged
