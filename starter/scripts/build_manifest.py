"""Build data/manifest.json with real, computed page/char statistics.

Run from `starter/`:  python scripts/build_manifest.py
Static fields (title, url, license, dates) are declared here; page lists and
character counts are measured from the local PDFs, never hand-typed.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingestion import load_pdf  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"

DOCS = [
    {
        "source_id": "ts2023",
        "title": "Taking Stock, August 2023: Making Public Investment Work for Growth",
        "local_file": "taking_stock_2023.pdf",
        "source_url": "https://openknowledge.worldbank.org/entities/publication/6f97a3f6-15a9-4301-877b-c65d3f951768",
        "doi": "https://doi.org/10.1596/40169",
        "license_or_permission": "CC BY-NC 3.0 IGO (World Bank Open Knowledge Repository)",
        "year": 2023,
    },
    {
        "source_id": "ts2024",
        "title": "Taking Stock August 2024: Reaching New Heights in Capital Markets",
        "local_file": "taking_stock_2024.pdf",
        "source_url": "https://openknowledge.worldbank.org/entities/publication/dcadbac5-a61d-4856-a789-9393491bc22f",
        "doi": "https://doi.org/10.1596/42084",
        "license_or_permission": "CC BY-NC 3.0 IGO (World Bank Open Knowledge Repository)",
        "year": 2024,
    },
]

PAGE_RULE = (
    "Content pages = physical PDF pages (1-based) whose normalized extracted "
    "text has >=10 characters. Covers, blank pages and image-only pages are "
    "excluded automatically and logged in results/extraction_issues.json. "
    "No page is counted twice."
)


def main() -> None:
    documents = []
    for doc in DOCS:
        pages, issues = load_pdf(DATA / doc["local_file"], doc["source_id"],
                                 doc["source_url"],
                                 metadata={"report": doc["source_id"],
                                           "year": doc["year"]})
        documents.append(doc | {
            "accessed_at": str(date.today()),
            "physical_pages": max([p.page for p in pages]
                                  + [i["page"] for i in issues], default=0),
            "content_pages": len(pages),
            "page_ids": [p.page for p in pages],
            "chars_total": sum(len(p.text) for p in pages),
            "chars_per_page": {str(p.page): len(p.text) for p in pages},
            "empty_or_failed_pages": [i["page"] for i in issues],
        })
        print(f"{doc['source_id']}: {len(pages)} content pages, "
              f"{documents[-1]['chars_total']} chars")

    manifest = {
        "corpus_topic": "Viet Nam economy - World Bank 'Taking Stock' biannual updates",
        "page_counting_rule": PAGE_RULE,
        "total_content_pages": sum(d["content_pages"] for d in documents),
        "note": "Same-topic reports from two different years give the corpus a "
                "trusted filter field (report/year) with clearly distinct values.",
        "documents": documents,
    }
    (DATA / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {DATA / 'manifest.json'} "
          f"(total content pages: {manifest['total_content_pages']})")


if __name__ == "__main__":
    main()
