"""Memory tests with a fake embedder (no model). Includes migration checks."""

from pathlib import Path

from agent.memory import MemoryStore, migrate_memory
from atelier.config import settings
from rag.manifest import IndexManifest
from rag.store import VectorStore


class FakeEmbedder:
    """Maps keyword presence to a tiny vector; last dim is a nonzero bias so
    cosine distance is always defined."""

    def _vec(self, text: str) -> list[float]:
        t = text.lower()
        return [
            1.0 if "apple" in t else 0.0,
            1.0 if "vector" in t else 0.0,
            1.0 if "license" in t else 0.0,
            0.1,
        ]

    def embed_passages(self, texts):
        return [self._vec(x) for x in texts]

    def embed_query(self, q):
        return self._vec(q)

    @property
    def dim(self):
        return 4

    model_name = "fake-embedding"


def _mem(tmp_path):
    store = VectorStore(path=str(tmp_path / "mem"), collection="mem_test")
    return MemoryStore(embedder=FakeEmbedder(), store=store)


def test_remember_and_recall(tmp_path) -> None:
    mem = _mem(tmp_path)
    mem.remember("I like apple pie", tags=["food"])
    mem.remember("vector databases are useful", tags=["tech"])

    assert mem.count() == 2
    top = mem.recall("apple", k=1)
    assert len(top) == 1
    assert "apple" in top[0].text
    assert top[0].tags == ["food"]


def test_all_and_forget(tmp_path) -> None:
    mem = _mem(tmp_path)
    mid = mem.remember("uses the Apache license", tags=["legal"])
    assert mem.count() == 1
    assert any(m.id == mid for m in mem.all())

    mem.forget(mid)
    assert mem.count() == 0


def test_persists_across_sessions(tmp_path) -> None:
    # "Session 1": write a fact, then drop the store object.
    s1 = VectorStore(path=str(tmp_path / "mem"), collection="mem_test")
    MemoryStore(embedder=FakeEmbedder(), store=s1).remember("apple fact", tags=[])

    # "Session 2": a brand-new store at the same path must see it.
    s2 = VectorStore(path=str(tmp_path / "mem"), collection="mem_test")
    mem2 = MemoryStore(embedder=FakeEmbedder(), store=s2)
    assert mem2.count() == 1
    assert "apple" in mem2.recall("apple", k=1)[0].text


def test_memory_migration_backups_and_preserves_records(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "memory_backup_dir", tmp_path / "backups")
    manifest = IndexManifest(tmp_path / "memory-manifest.sqlite3")
    store = VectorStore(path=str(tmp_path / "mem"), collection="old_memory")
    mem = MemoryStore(embedder=FakeEmbedder(), store=store, manifest=manifest)
    mem.remember("apple fact", tags=["food"])
    result = migrate_memory(embedder=FakeEmbedder(), manifest=manifest, store=store)
    assert result["before"] == result["after"] == 1
    assert Path(result["backup"]).exists()
    migrated = MemoryStore(embedder=FakeEmbedder(), manifest=manifest)
    assert migrated.count() == 1
    assert migrated.all()[0].tags == ["food"]
