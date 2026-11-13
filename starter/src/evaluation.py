"""Evaluate retrieved evidence against gold pages/quotes; keep full traces.

A retrieved chunk is a hit when its (document_id, page) is one of the
verified gold locations AND its normalized text contains the normalized
gold evidence quote (or one of the documented alternative quotes).
Page-match-only or quote-only is recorded separately, never silently
counted as a hit.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    gold_pages = question.get("gold_pages") or [
        {"document_id": question["gold_source_id"], "page": question["gold_page"]}
    ]
    quotes = [question["evidence_quote"]]
    quotes.extend(question.get("alternative_evidence", []))
    quotes_n = [_norm(q) for q in quotes if q]
    gold_keys = {(g["document_id"], int(g["page"])) for g in gold_pages}

    trace: list[dict[str, Any]] = []
    for rank, hit in enumerate(hits, start=1):
        meta = hit["metadata"]
        page_ok = (meta.get("document_id"), int(meta.get("page", -1))) in gold_keys
        text_n = _norm(hit["text"])
        quote_ok = any(q in text_n for q in quotes_n)
        trace.append({
            "rank": rank,
            "chunk_id": hit["chunk_id"],
            "score": hit["score"],
            "document_id": meta.get("document_id"),
            "page": meta.get("page"),
            "source": meta.get("source"),
            "page_matches_gold": page_ok,
            "contains_evidence": quote_ok,
            "is_hit": page_ok and quote_ok,
            "text": hit["text"],
        })

    hit_ranks = [t["rank"] for t in trace if t["is_hit"]]
    return {
        "question_id": question["id"],
        "split": question["split"],
        "strategy": question.get("_strategy"),
        "has_filter": bool(question.get("filter")),
        "hit_at_1": bool(hit_ranks and hit_ranks[0] == 1),
        "evidence_hit_at_3": bool(hit_ranks),
        "hit_ranks": hit_ranks,
        "evidence_split_across_chunks": (
            not hit_ranks
            and any(t["contains_evidence"] for t in trace)
        ),
        "top3": trace,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 / Evidence Hit@3 by strategy and split (n/N kept)."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        groups[(trace["strategy"], trace["split"])].append(trace)

    summary: dict[str, Any] = {}
    for (strategy, split), rows in sorted(groups.items()):
        n = len(rows)
        hit1 = sum(1 for r in rows if r["hit_at_1"])
        hit3 = sum(1 for r in rows if r["evidence_hit_at_3"])
        split_evidence = sum(1 for r in rows if r["evidence_split_across_chunks"])
        summary[f"{strategy}|{split}"] = {
            "hit@1": f"{hit1}/{n}", "hit@1_rate": round(hit1 / n, 4) if n else None,
            "evidence_hit@3": f"{hit3}/{n}",
            "evidence_hit@3_rate": round(hit3 / n, 4) if n else None,
            "evidence_in_top3_but_page_mismatch_or_split": split_evidence,
            "n": n,
        }
    return summary
