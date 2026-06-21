"""Vector-store round-trip using synthetic embeddings (no model download)."""

from rag.chunk import Chunk
from rag.store import VectorStore


def _chunk(text: str, idx: int) -> Chunk:
    return Chunk(text=text, source="notes.md", chunk_index=idx, metadata={"doc_type": "markdown"})


def test_add_query_and_count(tmp_path) -> None:
    store = VectorStore(path=str(tmp_path / "vs"), collection="test")
    chunks = [_chunk("apples and oranges", 0), _chunk("vector databases", 1)]
    # Two clearly separated points in 3-space.
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    n = store.add(chunks, embeddings)

    assert n == 2
    assert store.count() == 2

    hits = store.query([0.9, 0.1, 0.0], k=1)
    assert len(hits) == 1
    assert hits[0]["text"] == "apples and oranges"
    assert hits[0]["metadata"]["chunk_index"] == 0
    assert hits[0]["score"] > 0.8


def test_upsert_does_not_duplicate(tmp_path) -> None:
    store = VectorStore(path=str(tmp_path / "vs"), collection="test")
    store.add([_chunk("v1", 0)], [[1.0, 0.0, 0.0]])
    store.add([_chunk("v2 updated", 0)], [[1.0, 0.0, 0.0]])  # same id (source:0)

    assert store.count() == 1
    hits = store.query([1.0, 0.0, 0.0], k=1)
    assert hits[0]["text"] == "v2 updated"


def test_reset_clears(tmp_path) -> None:
    store = VectorStore(path=str(tmp_path / "vs"), collection="test")
    store.add([_chunk("x", 0)], [[1.0, 0.0, 0.0]])
    store.reset()
    assert store.count() == 0
