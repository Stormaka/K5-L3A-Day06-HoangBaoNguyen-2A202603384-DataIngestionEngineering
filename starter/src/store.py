"""Persistent vector store: local Chroma, cosine space, metadata filter.

One collection per strategy (day6_A / day6_B / day6_C). Upserts use stable
chunk IDs so re-ingesting the same corpus never duplicates; chunks of a
re-ingested document that no longer exist are deleted.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from .models import Chunk

STRATEGIES = ("A", "B", "C")


class ChromaStore:
    def __init__(self, persist_dir: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.persist_dir = str(Path(persist_dir))
        self.dimensions = dimensions
        self._client = chromadb.PersistentClient(path=self.persist_dir)
        self._collections: dict[str, Any] = {}

    def _collection(self, strategy: str):
        if strategy in self._collections:
            return self._collections[strategy]
        col = self._client.get_or_create_collection(
            name=f"day6_{strategy}",
            metadata={"hnsw:space": "cosine", "dimensions": self.dimensions},
        )
        stored_dims = (col.metadata or {}).get("dimensions")
        if stored_dims != self.dimensions:
            raise ValueError(
                f"collection day6_{strategy} has dimensions {stored_dims}, "
                f"expected {self.dimensions}; re-create the store."
            )
        self._collections[strategy] = col
        return col

    def create_schema(self) -> None:
        for strategy in STRATEGIES:
            self._collection(strategy)

    @staticmethod
    def _meta(chunk: Chunk) -> dict[str, Any]:
        flat: dict[str, Any] = {
            "document_id": chunk.document_id,
            "source": chunk.source,
            "page": chunk.page,
        }
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                flat[key] = value
        return flat

    def upsert(self, strategy: str, chunks: list[Chunk],
               vectors: list[list[float]]) -> dict[str, int]:
        if len(chunks) != len(vectors):
            raise ValueError(f"chunks ({len(chunks)}) vs vectors ({len(vectors)}) length mismatch")
        col = self._collection(strategy)
        written = 0
        for chunk, vector in zip(chunks, vectors):
            if len(vector) != self.dimensions:
                raise ValueError(
                    f"vector dim {len(vector)} != {self.dimensions} for {chunk.chunk_id}")
            col.upsert(
                ids=[chunk.chunk_id],
                embeddings=[vector],
                documents=[chunk.text],
                metadatas=[self._meta(chunk)],
            )
            written += 1

        # Drop obsolete chunks of the re-ingested documents (stable IDs make
        # unchanged chunks overwrite in place; vanished pages get deleted).
        deleted = 0
        for document_id in sorted({c.document_id for c in chunks}):
            existing = col.get(where={"document_id": document_id}, include=[])
            keep = {c.chunk_id for c in chunks if c.document_id == document_id}
            stale = [i for i in existing["ids"] if i not in keep]
            if stale:
                col.delete(ids=stale)
                deleted += len(stale)
        return {"written": written, "deleted_obsolete": deleted}

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError("query vector dimension mismatch")
        where: dict[str, Any] | None = None
        if filters:
            where = {key: {"$eq": value} for key, value in filters.items()}
        col = self._collection(strategy)
        result = col.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[dict[str, Any]] = []
        for i, cid in enumerate(result["ids"][0]):
            distance = result["distances"][0][i]
            hits.append({
                "chunk_id": cid,
                "text": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                # cosine distance -> similarity so higher is better
                "score": round(1.0 - distance, 6),
            })
        return hits

    def count(self, strategy: str) -> int:
        return self._collection(strategy).count()

    def drop_all(self) -> None:
        """Utility for a clean re-run from scratch (documented in README)."""
        for strategy in STRATEGIES:
            try:
                self._client.delete_collection(f"day6_{strategy}")
            except Exception:
                pass
        self._collections.clear()
