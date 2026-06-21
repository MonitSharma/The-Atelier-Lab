"""Retrieval: embed a query, fetch nearest chunks, format them for the prompt."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atelier.config import settings
from rag.embed import get_embedder
from rag.store import VectorStore


def retrieve(query: str, k: int | None = None, store: VectorStore | None = None) -> list[dict[str, Any]]:
    store = store or VectorStore()
    embedding = get_embedder().embed_query(query)
    return store.query(embedding, k=k)


def format_context(hits: list[dict[str, Any]], max_chars: int | None = None) -> str:
    """Render retrieved chunks into a numbered, citable context block."""
    max_chars = max_chars or settings.max_context_chars
    blocks: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        src = hit["metadata"].get("source", "?")
        name = Path(src).name if src != "?" else "?"
        section = hit["metadata"].get("section", "")
        header = f"[{i}] {name}" + (f"  ({section})" if section else "")
        body = hit["text"]
        block = f"{header}\n{body}"
        if used + len(block) > max_chars and blocks:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks)


def citations(hits: list[dict[str, Any]]) -> list[str]:
    """Short, de-duplicated source list for display under an answer."""
    seen: list[str] = []
    for hit in hits:
        name = Path(hit["metadata"].get("source", "?")).name
        if name not in seen:
            seen.append(name)
    return seen
