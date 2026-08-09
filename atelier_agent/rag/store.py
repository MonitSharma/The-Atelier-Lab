"""Persistent vector store over ChromaDB (local, file-backed, free).

We supply our own embeddings rather than letting Chroma call an embedding
function, so the store never needs network access and stays in lockstep with
:mod:`rag.embed`. Cosine space matches our normalized vectors.

Chunk IDs are derived from ``document_id:chunk_index`` when available, so a
path is a locator and content identity remains stable across renames.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import chromadb

from atelier.config import settings
from rag.chunk import Chunk


def _chunk_id(chunk: Chunk) -> str:
    document_id = chunk.metadata.get("document_id", chunk.source)
    raw = f"{document_id}:{chunk.chunk_index}".encode()
    return hashlib.sha1(raw).hexdigest()


class VectorStore:
    def __init__(self, path: str | None = None, collection: str | None = None) -> None:
        settings.ensure_dirs()
        self.path = path or str(settings.vector_dir)
        self._client = chromadb.PersistentClient(path=self.path)
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

    def replace_document(self, document_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
        """Upsert the replacement first, then remove stale tail chunks."""
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        new_ids = {_chunk_id(chunk) for chunk in chunks}
        self.add(chunks, embeddings)
        if self.count():
            found = self._collection.get(
                where={"document_id": document_id}, include=["metadatas"]
            )
            stale = [doc_id for doc_id in found.get("ids", []) if doc_id not in new_ids]
            self.delete(stale)
        return len(chunks)

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

    def upsert_raw(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """Low-level upsert with caller-supplied ids (used by memory)."""
        if not ids:
            return 0
        self._collection.upsert(ids=ids, documents=documents,
                                embeddings=embeddings, metadatas=metadatas)
        return len(ids)

    def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    def delete_source(self, source: str) -> int:
        """Remove all chunks belonging to one source before replacement."""
        if self.count() == 0:
            return 0
        found = self._collection.get(where={"source": source}, include=["metadatas"])
        ids = found.get("ids", [])
        self.delete(ids)
        return len(ids)

    def delete_document(self, document_id: str) -> int:
        if self.count() == 0:
            return 0
        found = self._collection.get(
            where={"document_id": document_id}, include=["metadatas"]
        )
        ids = found.get("ids", [])
        self.delete(ids)
        return len(ids)

    def relocate_document(self, document_id: str, source: str) -> int:
        """Update the filesystem locator without touching embeddings."""
        if self.count() == 0:
            return 0
        found = self._collection.get(
            where={"document_id": document_id}, include=["metadatas"]
        )
        ids = found.get("ids", [])
        metadatas = []
        for metadata in found.get("metadatas", []):
            updated = dict(metadata or {})
            updated["source"] = source
            updated["filename"] = Path(source).name
            metadatas.append(updated)
        if ids:
            self._collection.update(ids=ids, metadatas=metadatas)
        return len(ids)

    def get_all(self) -> dict[str, Any]:
        return self._collection.get(include=["documents", "metadatas"])

    def count(self) -> int:
        return self._collection.count()

    def embedding_dimension(self) -> int | None:
        if self.count() == 0:
            return None
        got = self._collection.get(limit=1, include=["embeddings"])
        embeddings = got.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return None
        return len(embeddings[0])

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
