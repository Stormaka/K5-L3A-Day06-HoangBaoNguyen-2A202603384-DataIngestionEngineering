"""Re-export the coherence audit sample on CONTENT pages only.

The initial run sampled the first 10 sorted extracted pages, which were mostly
front-matter (cover/TOC/abbreviations). Per GUIDE.md the coherence sample
should cover content; the sampling rule was re-declared to "first 10 sorted
CONTENT page IDs per the manifest rule" BEFORE the new sample was scored.
Retrieval metrics, traces and the grounding/metadata audits are unaffected.

Run from `starter/`:  python scripts/export_coherence_sample.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import chunking  # noqa: E402
from src.ingestion import load_pdf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
RESULTS = REPO / "results"


def main() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    content_ids = {(d["source_id"], p) for d in manifest["documents"]
                   for p in d["page_ids"]}

    pages = []
    for doc in manifest["documents"]:
        doc_pages, _ = load_pdf(DATA / doc["local_file"], doc["source_id"],
                                doc["source_url"],
                                metadata={"report": doc["source_id"],
                                          "year": doc["year"]})
        pages.extend(p for p in doc_pages
                     if (p.document_id, p.page) in content_ids)

    sample = sorted(pages, key=lambda p: (p.document_id, p.page))[:10]
    out = []
    for page in sample:
        a = chunking.fixed_size(page, size=500, overlap=50)
        b = chunking.by_paragraph(page, max_size=1000, merge_min=150)
        out.append({
            "position": f"{page.document_id}:p{page.page}",
            "page_text_excerpt": page.text[:600],
            "sampling_rule": "first 10 sorted CONTENT pages (manifest rule); "
                             "declared before scoring",
            "A_chunks": [{"chunk_id": c.chunk_id, "text": c.text} for c in a],
            "B_chunks": [{"chunk_id": c.chunk_id, "text": c.text} for c in b],
        })
        print(f"{page.document_id}:p{page.page}  A={len(a)} chunks, B={len(b)} chunks")

    (RESULTS / "coherence_sample.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {RESULTS / 'coherence_sample.json'} ({len(out)} positions)")


if __name__ == "__main__":
    main()
