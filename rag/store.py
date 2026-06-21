"""Persistent vector store over ChromaDB (local, file-backed, free).

We supply our own embeddings rather than letting Chroma call an embedding
function, so the store never needs network access and stays in lockstep with
:mod:`rag.embed`. Cosine space matches our normalized vectors.

IDs are derived from ``source:chunk_index`` and written with ``upsert`` so that
re-ingesting a changed file refreshes its chunks instead of duplicating them.
"""

from __future__ import annotations

import hashlib
from typing import Any

import chromadb

from atelier.config import settings
from rag.chunk import Chunk


def _chunk_id(chunk: Chunk) -> str:
    raw = f"{chunk.source}:{chunk.chunk_index}".encode()
    return hashlib.sha1(raw).hexdigest()


class VectorStore:
    def __init__(self, path: str | None = None, collection: str | None = None) -> None:
        settings.ensure_dirs()
        self._client = chromadb.PersistentClient(path=path or str(settings.vector_dir))
        self._collection = self._client.get_or_create_collection(
            name=collection or settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        ids = [_chunk_id(c) for c in chunks]
        documents = [c.text for c in chunks]
        metadatas: list[dict[str, Any]] = []
        for c in chunks:
            meta = dict(c.metadata)
            meta["source"] = c.source
            meta["chunk_index"] = c.chunk_index
            metadatas.append(meta)
        self._collection.upsert(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )
        return len(ids)

    def query(self, embedding: list[float], k: int | None = None) -> list[dict[str, Any]]:
        k = k or settings.retrieval_k
        if self.count() == 0:
            return []
        res = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        hits: list[dict[str, Any]] = []
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            hits.append({
                "text": doc,
                "metadata": meta,
                "distance": dist,
                "score": 1.0 - dist,  # cosine distance -> similarity
            })
        return hits

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Drop and recreate the collection (start the index over)."""
        name = self._collection.name
        self._client.delete_collection(name)
        self._collection = self._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )

    def sources(self) -> list[str]:
        """Distinct source files currently indexed."""
        if self.count() == 0:
            return []
        got = self._collection.get(include=["metadatas"])
        seen = {m.get("source", "") for m in got.get("metadatas", [])}
        return sorted(s for s in seen if s)
