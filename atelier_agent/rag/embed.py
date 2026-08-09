"""Local text embeddings through the Ollama embedding API.

The canonical Atelier retrieval model is Qwen3-Embedding-4B. Queries receive
the validated scientific-retrieval instruction from configuration; stored
passages remain unmodified. The model is loaded by Ollama on first use and
Ollama returns the model's embedding vectors directly; Chroma is configured
for cosine distance, matching the validated retrieval experiment.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from atelier.config import settings


class Embedder:
    """Wraps Ollama's local embedding endpoint."""

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        self.model_name = model_name or settings.embed_model
        self.base_url = settings.ollama_url.rstrip("/")
        self._dim: int | None = None

    def _embed(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({
            "model": self.model_name,
            "input": texts,
            "truncate": False,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.request_timeout) as response:
                data = json.load(response)
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Ollama at {self.base_url}; start `ollama serve`"
            ) from exc
        vectors = data.get("embeddings")
        if not vectors or any(not isinstance(v, list) for v in vectors):
            raise RuntimeError(f"Ollama returned no usable embeddings: {data}")
        self._dim = len(vectors[0])
        return vectors

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._embed([""])
        return self._dim or 0

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self._embed(texts)

    def embed_query(self, query: str) -> list[float]:
        prompt = f"Instruct: {settings.query_instruction}\nQuery: {query}"
        return self._embed([prompt])[0]


_default: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the process-wide embedder, creating it on first use."""
    global _default
    if _default is None:
        _default = Embedder()
    return _default
