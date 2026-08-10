"""Friendly compatibility checks between an embedding config and Chroma."""

from __future__ import annotations

from rag.manifest import IndexManifest
from rag.store import VectorStore


class IndexCompatibilityError(RuntimeError):
    pass


def ensure_compatible(store: VectorStore, manifest: IndexManifest, embedder) -> None:
    if store.count() == 0:
        return
    state = manifest.state()
    stored_model = state.get("embedding_model")
    stored_dim = int(state["embedding_dimension"]) if state.get("embedding_dimension", "").isdigit() else store.embedding_dimension()
    current_dim = embedder.dim
    if stored_model and stored_model != embedder.model_name:
        raise IndexCompatibilityError(
            f"The knowledge index was built with {stored_model} ({stored_dim or '?'}D) "
            f"but Atelier is configured for {embedder.model_name} ({current_dim}D). "
            "Rebuild with: atelier ingest --reset <path>"
        )
    if stored_dim and stored_dim != current_dim:
        raise IndexCompatibilityError(
            f"The knowledge index has {stored_dim}D vectors but Atelier is configured "
            f"for {embedder.model_name} ({current_dim}D). "
            "Rebuild with: atelier ingest --reset <path>"
        )
