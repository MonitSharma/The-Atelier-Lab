"""Local text embeddings via sentence-transformers (Apple-Silicon GPU / MPS).

The model is loaded lazily and cached as a module singleton — loading weights
costs a second or two, so we do it once. ``bge-base-en-v1.5`` wants a short
instruction prepended to *queries* (not passages) for best retrieval; we honor
that distinction with :meth:`embed_query` vs :meth:`embed_passages`.
"""

from __future__ import annotations

import numpy as np

from atelier.config import settings


def _pick_device(preferred: str) -> str:
    try:
        import torch
    except Exception:  # noqa: BLE001
        return "cpu"
    if preferred == "mps" and torch.backends.mps.is_available():
        return "mps"
    if preferred == "cuda" and torch.cuda.is_available():
        return "cuda"
    return "cpu"


class Embedder:
    """Wraps a sentence-transformers model with normalized output."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        self.model_name = model_name or settings.embed_model
        self.device = _pick_device(device or settings.embed_device)
        self._model = None  # lazy

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def dim(self) -> int:
        # method was renamed across sentence-transformers versions
        getter = getattr(self.model, "get_embedding_dimension", None) or \
            self.model.get_sentence_embedding_dimension
        return int(getter())

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(
            texts,
            batch_size=settings.embed_batch_size,
            normalize_embeddings=True,  # so cosine == dot product
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 256,
        )

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._encode(texts).tolist()

    def embed_query(self, query: str) -> list[float]:
        prompt = f"{settings.query_instruction}{query}"
        return self._encode([prompt])[0].tolist()


_default: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the process-wide embedder, creating it on first use."""
    global _default
    if _default is None:
        _default = Embedder()
    return _default
