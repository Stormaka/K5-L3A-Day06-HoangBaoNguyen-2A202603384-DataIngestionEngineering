"""Build data/manifest.json with real, computed page/char statistics.

Run from `starter/`:  python scripts/build_manifest.py
Static fields (title, url, license, dates) are declared here; page lists and
character counts are measured from the local PDFs, never hand-typed.

Page classification follows GUIDE.md: structural pages (cover, copyright,
contents/figures/tables/abbreviation lists, acknowledgements, references,
stubs under 200 chars) are excluded from the content-page count; they stay
in the extraction log with a reason. Content pages are what must total >=30.
"""
from __future__ import annotations

import json
import re
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
    "text is >=200 characters AND is not a structural page. Structural pages "
    "(excluded, with reason): cover ('Public Disclosure Authorized'), "
    "copyright ('All queries on rights and licenses'), section lists "
    "(standalone line: CONTENTS/FIGURES/BOXES/TABLES/ABBREVIATIONS/"
    "ACKNOWLEDGEMENTS/REFERENCES), abbreviation-list pages (>=60% of lines "
    "look like 'ABBR term'), and stubs <200 chars. Extraction itself keeps "
    "every page with >=10 chars (logged in results/extraction_issues.json), "
    "so nothing is silently dropped; only the content-page COUNT excludes "
    "structural pages, per GUIDE.md. No page is counted twice."
)

_SECTION_LIST_LINE = re.compile(
    r"^\s*\d{0,3}\s*(contents|figures|boxes|tables|abbreviations|"
    r"acknowledgements|acknowledgments|references)\s*[.]?\s*$", re.IGNORECASE)
_ABBREV_LINE = re.compile(r"^[A-Z][A-Za-z0-9&/.\-]{0,15}\s+[A-Z][A-Za-z].*")


def structural_reason(text: str) -> str | None:
    """Classify a normalized page as structural (front/back matter) or not."""
    if "Public Disclosure Authorized" in text:
        return "cover/disclosure"
    if "All queries on rights and licenses" in text:
        return "copyright"
    lines = [l for l in text.split("\n") if l.strip()]
    if any(_SECTION_LIST_LINE.match(l) for l in lines):
        return "section-list (contents/figures/tables/abbrev/ack/references)"
    if len(lines) >= 6:
        abbrev = sum(1 for l in lines
                     if _ABBREV_LINE.match(l) and 4 < len(l) < 90)
        if abbrev / len(lines) >= 0.6:
            return "abbreviation-list"
    if len(text) < 200:
        return "stub <200 chars"
    return None


def main() -> None:
    documents = []
    for doc in DOCS:
        pages, issues = load_pdf(DATA / doc["local_file"], doc["source_id"],
                                 doc["source_url"],
                                 metadata={"report": doc["source_id"],
                                           "year": doc["year"]})
        content, structural = [], {}
        for p in pages:
            reason = structural_reason(p.text)
            if reason:
                structural[p.page] = reason
            else:
                content.append(p)
        print(f"{doc['source_id']}: extracted={len(pages)} "
              f"content={len(content)} structural={len(structural)}")
        for page, reason in sorted(structural.items()):
            print(f"    p{page}: {reason}")
        documents.append(doc | {
            "accessed_at": str(date.today()),
            "physical_pages": max([p.page for p in pages]
                                  + [i["page"] for i in issues], default=0),
            "content_pages": len(content),
            "page_ids": [p.page for p in content],
            "chars_total": sum(len(p.text) for p in content),
            "chars_per_page": {str(p.page): len(p.text) for p in content},
            "structural_pages": structural,
            "empty_or_failed_pages": [i["page"] for i in issues],
        })

    manifest = {
        "corpus_topic": "Viet Nam economy - World Bank 'Taking Stock' biannual updates",
        "page_counting_rule": PAGE_RULE,
        "total_extracted_pages": sum(d["physical_pages"] and
                                     len(d["chars_per_page"]) +
                                     len(d["structural_pages"]) for d in documents),
        "total_content_pages": sum(d["content_pages"] for d in documents),
        "note": "Same-topic reports from two different years give the corpus a "
                "trusted filter field (report/year) with clearly distinct values.",
        "documents": documents,
    }
    (DATA / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {DATA / 'manifest.json'} "
          f"(content pages: {manifest['total_content_pages']})")


if __name__ == "__main__":
    main()
