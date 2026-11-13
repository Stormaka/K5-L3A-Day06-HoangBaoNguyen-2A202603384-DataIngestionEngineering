"""Real embedding provider: local Sentence Transformers multilingual MiniLM.

Query and document texts are encoded identically (this model uses no
instruction prefixes); vectors are L2-normalized so cosine similarity is a
dot product. No mock fallback: provider errors propagate to the caller.
"""
from __future__ import annotations

import os


class MyEmbedder:
    model_name: str
    dimensions: int

    def __init__(self, model_name: str = "sentence-transformers/"
                 "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        # HF_ENDPOINT can point at a mirror when huggingface.co is
        # unreachable from the local network; it must be set before import.
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)
        get_dim = getattr(self._model, "get_embedding_dimension", None) or \
            self._model.get_sentence_embedding_dimension
        dim = get_dim()
        if not dim:
            raise ValueError(f"model {model_name} reported no embedding dimension")
        self.dimensions = int(dim)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(
            texts, batch_size=32, normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vectors]

    def embed_query(self, question: str) -> list[float]:
        vector = self._model.encode(
            [question], normalize_embeddings=True, show_progress_bar=False
        )[0]
        return vector.tolist()


def provider_info() -> dict:
    """Report provider details for the report/log (honesty requirement)."""
    import sentence_transformers
    import torch
    return {
        "provider": "local",
        "library": f"sentence-transformers {sentence_transformers.__version__}",
        "torch": torch.__version__,
        "hf_endpoint": os.environ.get("HF_ENDPOINT", "https://huggingface.co (default)"),
        "query_document_handling": "identical encoding, no instruction prefix, "
                                   "L2-normalized, cosine metric",
    }
