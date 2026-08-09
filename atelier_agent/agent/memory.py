"""Persistent semantic memory with safe embedding migration."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from atelier.config import settings
from rag.compat import IndexCompatibilityError
from rag.manifest import IndexManifest
from rag.store import VectorStore

MEMORY_COLLECTION = "atelier_memory"


class _LocalManifest:
    """Dependency-injection fallback used by tests/custom stores."""

    def __init__(self):
        self.values: dict[str, str] = {}

    def state(self) -> dict[str, str]:
        return dict(self.values)

    def set_state(self, **values: Any) -> None:
        self.values.update({key: str(value) for key, value in values.items()})


@dataclass
class Memory:
    id: str
    text: str
    tags: list[str]
    created_at: str
    score: float | None = None


def _new_id(text: str) -> str:
    return hashlib.sha1(f"{text}:{time.time_ns()}".encode()).hexdigest()[:16]


class MemoryStore:
    """Persistent semantic memory. The collection is selected by a manifest."""

    def __init__(self, embedder: Any = None, store: VectorStore | None = None,
                 manifest: IndexManifest | None = None) -> None:
        self._embedder = embedder
        self._manifest = manifest or (IndexManifest(settings.memory_manifest_path) if store is None else _LocalManifest())
        state = self._manifest.state()
        active = state.get("active_collection", MEMORY_COLLECTION)
        vector_path = state.get("vector_path", str(settings.vector_dir))
        self._store = store or VectorStore(path=vector_path, collection=active)

    @property
    def embedder(self):
        if self._embedder is None:
            from rag.embed import get_embedder

            self._embedder = get_embedder()
        return self._embedder

    def _check_compatible(self) -> None:
        if self._store.count() == 0:
            return
        state = self._manifest.state()
        current_model = getattr(self.embedder, "model_name", settings.embed_model)
        current_dim = getattr(self.embedder, "dim", None)
        stored_model = state.get("embedding_model")
        stored_dim = int(state["embedding_dimension"]) if state.get("embedding_dimension", "").isdigit() else self._store.embedding_dimension()
        if (stored_model and stored_model != current_model) or (stored_dim and current_dim and stored_dim != current_dim):
            raise IndexCompatibilityError(
                "Semantic memory uses an incompatible embedding index. "
                f"Stored: {stored_model or 'unknown'} ({stored_dim or '?'}D); "
                f"current: {current_model} ({current_dim or '?'}D). "
                "Run `atelier memory-migrate` before recalling or adding memories."
            )

    def remember(self, text: str, tags: list[str] | None = None) -> str:
        text = text.strip()
        if not text:
            raise ValueError("cannot remember empty text")
        self._check_compatible()
        mid = _new_id(text)
        embedding = self.embedder.embed_passages([text])[0]
        self._store.upsert_raw(
            ids=[mid], documents=[text], embeddings=[embedding], metadatas=[{
                "tags": ",".join(tags or []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }],
        )
        self._manifest.set_state(
            active_collection=self._store._collection.name,
            vector_path=self._store.path,
            embedding_model=getattr(self.embedder, "model_name", settings.embed_model),
            embedding_dimension=len(embedding), index_schema_version=settings.index_schema_version,
        )
        return mid

    def recall(self, query: str, k: int = 5) -> list[Memory]:
        if self._store.count() == 0:
            return []
        self._check_compatible()
        hits = self._store.query(self.embedder.embed_query(query), k=k)
        return [Memory(
            id="", text=h["text"],
            tags=[t for t in h["metadata"].get("tags", "").split(",") if t],
            created_at=h["metadata"].get("created_at", ""),
            score=round(float(h["score"]), 3),
        ) for h in hits]

    def all(self) -> list[Memory]:
        got = self._store.get_all()
        return [Memory(
            id=mid, text=doc,
            tags=[t for t in (meta or {}).get("tags", "").split(",") if t],
            created_at=(meta or {}).get("created_at", ""),
        ) for mid, doc, meta in zip(
            got.get("ids", []), got.get("documents", []), got.get("metadatas", []), strict=False
        )]

    def forget(self, memory_id: str) -> None:
        self._store.delete([memory_id])

    def count(self) -> int:
        return self._store.count()


def migrate_memory(*, embedder: Any = None, manifest: IndexManifest | None = None,
                   store: VectorStore | None = None) -> dict[str, Any]:
    """Create a verified new collection and activate it without deleting the old one."""
    manifest = manifest or IndexManifest(settings.memory_manifest_path)
    active = manifest.state().get("active_collection", MEMORY_COLLECTION)
    old_store = store or VectorStore(collection=active)
    old_mem = MemoryStore(embedder=embedder, store=old_store, manifest=manifest)
    records = old_mem.all()
    settings.ensure_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = settings.memory_backup_dir / f"memory-{stamp}.json"
    backup.write_text(json.dumps([
        {"id": m.id, "text": m.text, "tags": m.tags, "created_at": m.created_at}
        for m in records
    ], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    embedder = embedder or old_mem.embedder
    vectors = embedder.embed_passages([m.text for m in records]) if records else []
    new_collection = f"atelier_memory_{stamp}"
    new_store = VectorStore(path=old_store.path, collection=new_collection)
    ids = [m.id for m in records]
    metadatas = [{"tags": ",".join(m.tags), "created_at": m.created_at} for m in records]
    new_store.upsert_raw(ids, [m.text for m in records], vectors, metadatas)
    if new_store.count() != len(records):
        raise RuntimeError("Memory migration verification failed; old collection remains active")
    manifest.set_state(
        active_collection=new_collection,
        vector_path=old_store.path,
        embedding_model=getattr(embedder, "model_name", settings.embed_model),
        embedding_dimension=getattr(embedder, "dim", len(vectors[0]) if vectors else 0),
        migration_backup=str(backup), index_schema_version=settings.index_schema_version,
    )
    return {"before": len(records), "after": new_store.count(), "backup": str(backup), "collection": new_collection}


_default: MemoryStore | None = None


def get_memory() -> MemoryStore:
    global _default
    if _default is None:
        _default = MemoryStore()
    return _default
