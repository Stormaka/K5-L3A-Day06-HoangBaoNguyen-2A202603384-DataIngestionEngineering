"""Day 06 pipeline orchestrator: corpus -> chunks -> embeddings -> store ->
retrieval benchmark for strategies A/B/C with full traces and audit exports.

Run from `starter/`:  python -m src.run
Environment: HF_ENDPOINT may point to a mirror if huggingface.co is blocked.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from . import chunking, evaluation
from .embeddings import MyEmbedder, provider_info
from .ingestion import load_pdf
from .models import DocumentPage
from .store import ChromaStore

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
BENCH = REPO / "benchmark"
RESULTS = REPO / "results"
CHROMA_DIR = RESULTS / "chroma"

MIN_CONTENT_PAGES = 30
TOP_K = 3
STRATEGY_DESC = {
    "A": "fixed-size 500 chars, overlap 50, no filter",
    "B": "paragraph/heading-aware chunks (max 1000), no filter",
    "C": "same chunks as B; metadata filter applied when question provides one",
}


def _load_corpus() -> tuple[list[DocumentPage], dict]:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    pages: list[DocumentPage] = []
    for doc in manifest["documents"]:
        doc_pages, _ = load_pdf(
            DATA / doc["local_file"], doc["source_id"], doc["source_url"],
            metadata={"report": doc["source_id"], "year": doc["year"],
                      "title": doc["title"]},
        )
        pages.extend(doc_pages)
        print(f"  {doc['source_id']}: {len(doc_pages)} content pages")
    if len(pages) < MIN_CONTENT_PAGES:
        raise SystemExit(
            f"corpus has {len(pages)} content pages < {MIN_CONTENT_PAGES} required")
    return pages, manifest


def _chunk_stats(chunks) -> dict:
    lengths = [len(c.text) for c in chunks]
    return {
        "chunk_count": len(chunks),
        "total_chars": sum(lengths),
        "est_tokens_chars_over_4": round(sum(lengths) / 4),
        "len_min": min(lengths), "len_max": max(lengths),
        "len_mean": round(statistics.mean(lengths), 1),
        "len_median": statistics.median(lengths),
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    t_start = time.perf_counter()

    print("[1/6] Loading corpus ...")
    pages, manifest = _load_corpus()
    content_total = manifest.get("total_content_pages", len(pages))
    if content_total < MIN_CONTENT_PAGES:
        raise SystemExit(
            f"manifest counts {content_total} content pages "
            f"< {MIN_CONTENT_PAGES} required")
    print(f"  extracted pages: {len(pages)} | content pages (per manifest "
          f"rule): {content_total} (OK, >= {MIN_CONTENT_PAGES})")

    print("[2/6] Chunking A (fixed 500/50) and B (paragraph, max 1000) ...")
    chunks_a, chunks_b = [], []
    for page in pages:
        chunks_a.extend(chunking.fixed_size(page, size=500, overlap=50))
        chunks_b.extend(chunking.by_paragraph(page, max_size=1000, merge_min=150))
    chunks_c = list(chunks_b)  # C differs from B only in retrieval-time filter

    print("[3/6] Embedding with one shared real model ...")
    embedder = MyEmbedder()
    print(f"  model: {embedder.model_name} | dim {embedder.dimensions}")

    def embed_all(chunks, label):
        t0 = time.perf_counter()
        vectors = embedder.embed_documents([c.text for c in chunks])
        return vectors, round(time.perf_counter() - t0, 2)

    vectors_a, t_emb_a = embed_all(chunks_a, "A")
    vectors_b, t_emb_b = embed_all(chunks_b, "B")
    # C stores B's chunks verbatim; identical texts -> reuse the same vectors.
    vectors_c = vectors_b

    print("[4/6] Storing vectors (Chroma, cosine) per strategy + reload check ...")
    store = ChromaStore(str(CHROMA_DIR), embedder.dimensions)
    store.create_schema()
    timings = {"embed_A_s": t_emb_a, "embed_B_s": t_emb_b}
    ingest_stats: dict = {}
    for strategy, chunks, vectors in (("A", chunks_a, vectors_a),
                                      ("B", chunks_b, vectors_b),
                                      ("C", chunks_c, vectors_c)):
        t0 = time.perf_counter()
        res = store.upsert(strategy, chunks, vectors)
        timings[f"ingest_{strategy}_s"] = round(time.perf_counter() - t0, 2)
        ingest_stats[strategy] = _chunk_stats(chunks) | res | {"desc": STRATEGY_DESC[strategy]}

    # Idempotence: re-ingest the same corpus must not duplicate anything.
    before = {s: store.count(s) for s in ("A", "B", "C")}
    for strategy, chunks, vectors in (("A", chunks_a, vectors_a),
                                      ("B", chunks_b, vectors_b),
                                      ("C", chunks_c, vectors_c)):
        store.upsert(strategy, chunks, vectors)
    after = {s: store.count(s) for s in ("A", "B", "C")}
    idempotence = {"counts_before_reingest": before, "counts_after_reingest": after,
                   "no_duplicates": before == after}
    (RESULTS / "idempotence_check.json").write_text(
        json.dumps(idempotence, indent=2), encoding="utf-8")

    print("[5/6] Running benchmark questions for A/B/C ...")
    payload = json.loads((BENCH / "questions.json").read_text(encoding="utf-8"))
    questions = payload["questions"] if isinstance(payload, dict) else payload
    traces: list[dict] = []
    query_vectors: dict[str, list[float]] = {}
    t_search = {"A": 0.0, "B": 0.0, "C": 0.0}
    for question in questions:
        if question["id"] not in query_vectors:
            query_vectors[question["id"]] = embedder.embed_query(question["question"])
    for strategy in ("A", "B", "C"):
        for question in questions:
            filters = question.get("filter") if strategy == "C" else None
            t0 = time.perf_counter()
            hits = store.search(strategy, query_vectors[question["id"]],
                                top_k=TOP_K, filters=filters)
            t_search[strategy] += time.perf_counter() - t0
            q = dict(question)
            q["_strategy"] = strategy
            traces.append(evaluation.evaluate_query(q, hits))

    with (RESULTS / "traces.jsonl").open("w", encoding="utf-8") as fh:
        for trace in traces:
            fh.write(json.dumps(trace, ensure_ascii=False) + "\n")

    metrics = {
        "model": embedder.model_name,
        "dimensions": embedder.dimensions,
        "provider": provider_info(),
        "store": {"type": "Chroma PersistentClient (local disk)",
                  "path": str(CHROMA_DIR), "metric": "cosine",
                  "search": "exact (Chroma local HNSW brute-force on small data)"},
        "summary": evaluation.summarize(traces),
        "timings_s": timings | {f"search_{k}_s": round(v, 3) for k, v in t_search.items()},
        "wall_clock_s": round(time.perf_counter() - t_start, 2),
        "cost_usd": 0.0,
    }
    (RESULTS / "metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "ingest_stats.json").write_text(
        json.dumps(ingest_stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[6/6] Exporting manual-audit samples ...")
    content_ids = {(d["source_id"], p) for d in manifest["documents"]
                   for p in d["page_ids"]}
    _export_audit_samples(pages, questions, store, query_vectors,
                          chunks_a, chunks_b, content_ids)

    print("\n=== Summary (Hit@1 | Evidence Hit@3) ===")
    for key, row in metrics["summary"].items():
        print(f"  {key:10s} hit@1 {row['hit@1']:8s} evidence_hit@3 {row['evidence_hit@3']}")
    print(f"  ingest counts A/B/C: {ingest_stats['A']['chunk_count']}"
          f"/{ingest_stats['B']['chunk_count']}/{ingest_stats['C']['chunk_count']}"
          f" | reload no-dup: {idempotence['no_duplicates']}"
          f" | cost: $0 | wall: {metrics['wall_clock_s']}s")


def _export_audit_samples(pages, questions, store, query_vectors, chunks_a,
                          chunks_b, content_page_ids=None) -> None:
    """Fixed sample sets for the manual 5-dimension assessment."""
    # Coherence: first 10 sorted CONTENT page IDs (manifest rule: structural
    # front/back-matter pages excluded), chosen before looking at scores.
    if content_page_ids:
        pages = [p for p in pages
                 if (p.document_id, p.page) in content_page_ids]
    sample_pages = sorted(pages, key=lambda p: (p.document_id, p.page))[:10]
    by_page_a: dict[tuple, list] = {}
    by_page_b: dict[tuple, list] = {}
    for c in chunks_a:
        by_page_a.setdefault((c.document_id, c.page), []).append(
            {"chunk_id": c.chunk_id, "text": c.text})
    for c in chunks_b:
        by_page_b.setdefault((c.document_id, c.page), []).append(
            {"chunk_id": c.chunk_id, "text": c.text})
    coherence_sample = [
        {"position": f"{p.document_id}:p{p.page}",
         "page_text_excerpt": p.text[:600],
         "A_chunks": by_page_a.get((p.document_id, p.page), []),
         "B_chunks": by_page_b.get((p.document_id, p.page), [])}
        for p in sample_pages
    ]
    (RESULTS / "coherence_sample.json").write_text(
        json.dumps(coherence_sample, indent=2, ensure_ascii=False), encoding="utf-8")

    # Metadata + grounding audits: the 5 test questions, top-3 for each strategy.
    test_qs = [q for q in questions if q["split"] == "test"]
    audit = []
    for q in test_qs:
        per_strategy = {}
        for strategy in ("A", "B", "C"):
            filters = q.get("filter") if strategy == "C" else None
            hits = store.search(strategy, query_vectors[q["id"]], top_k=TOP_K,
                                filters=filters)
            per_strategy[strategy] = [
                {"chunk_id": h["chunk_id"], "score": h["score"],
                 "metadata": h["metadata"], "text": h["text"]} for h in hits]
        audit.append({
            "question_id": q["id"], "question": q["question"],
            "expected_answer": q["expected_answer"],
            "evidence_quote": q["evidence_quote"],
            "gold_pages": q.get("gold_pages") or [
                {"document_id": q["gold_source_id"], "page": q["gold_page"]}],
            "filter": q.get("filter"), "results": per_strategy,
        })
    (RESULTS / "metadata_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    (RESULTS / "grounding_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
