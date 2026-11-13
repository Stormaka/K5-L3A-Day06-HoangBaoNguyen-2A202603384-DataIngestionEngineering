"""Verify every benchmark question's evidence before any retrieval run.

For each question: the normalized evidence quote must be a substring of the
normalized gold page text. The script then records ALL pages that contain the
quote as accepted gold locations (documented alternative evidence) and fails
loudly on any question whose evidence cannot be verified.

Run from `starter/`:  python scripts/verify_benchmark.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion import load_pdf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
BENCH = REPO / "benchmark"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> None:
    payload = json.loads((BENCH / "questions.json").read_text(encoding="utf-8"))
    questions = payload["questions"] if isinstance(payload, dict) else payload
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))

    pages = {}
    for doc in manifest["documents"]:
        doc_pages, _ = load_pdf(DATA / doc["local_file"], doc["source_id"],
                                doc["source_url"])
        for p in doc_pages:
            pages[(doc["source_id"], p.page)] = _norm(p.text)

    problems = []
    for q in questions:
        quotes = [q["evidence_quote"]] + q.get("alternative_evidence", [])
        matches = []
        for qi, quote in enumerate(quotes):
            quote_n = _norm(quote)
            found = [{"document_id": d, "page": p, "quote_index": qi}
                     for (d, p), text in pages.items() if quote_n in text]
            if not found:
                problems.append(f"{q['id']}: quote #{qi} not found on ANY page")
            matches.extend(found)
        primary = {"document_id": q["gold_source_id"], "page": q["gold_page"]}
        if primary not in [{"document_id": m["document_id"], "page": m["page"]}
                           for m in matches]:
            problems.append(f"{q['id']}: primary gold page does not contain the quote")
        q["gold_pages"] = sorted(
            {frozenset({"document_id": m["document_id"], "page": m["page"]}.items())
             for m in matches},
            key=lambda fs: dict(fs)["page"],
        )
        q["gold_pages"] = [dict(fs) for fs in q["gold_pages"]]

    summary = {
        "questions": len(questions),
        "dev": sum(1 for q in questions if q["split"] == "dev"),
        "test": sum(1 for q in questions if q["split"] == "test"),
        "filter_questions": sum(1 for q in questions if q.get("filter")),
        "filter_in_test": sum(1 for q in questions
                              if q.get("filter") and q["split"] == "test"),
        "types": {t: sum(1 for q in questions if q["type"] == t)
                  for t in {q["type"] for q in questions}},
    }
    print(json.dumps(summary, indent=2))

    if problems:
        print("\nEVIDENCE PROBLEMS:")
        for p in problems:
            print(" -", p)
        sys.exit(1)

    payload["questions"] = questions
    (BENCH / "questions.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    (BENCH / "verification.json").write_text(
        json.dumps({"status": "all evidence verified on gold pages",
                    **summary,
                    "gold_locations_per_question": {
                        q["id"]: q["gold_pages"] for q in questions}},
                   indent=2, ensure_ascii=False),
        encoding="utf-8")
    print("all evidence verified; questions.json updated with full gold page lists")


if __name__ == "__main__":
    main()
