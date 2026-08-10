"""Hybrid-retrieval unit tests: BM25 ranking + RRF fusion (no model)."""

import rag.lexical as lexical_module
from rag.lexical import BM25Index, get_bm25
from rag.retrieve import _rrf_fuse

DOCS = [
    "the quick brown fox jumps",
    "vector databases store embeddings for search",
    "the lazy dog sleeps all day",
]
METAS = [{"source": f"d{i}.md"} for i in range(len(DOCS))]


def test_bm25_ranks_keyword_match_first() -> None:
    idx = BM25Index(DOCS, METAS)
    hits = idx.search("vector embeddings search", n=3)
    assert hits, "expected matches"
    assert "vector databases" in hits[0]["text"]


def test_bm25_returns_only_matches() -> None:
    idx = BM25Index(DOCS, METAS)
    hits = idx.search("quick fox", n=5)
    assert all(h["score"] > 0 for h in hits)
    assert "quick brown fox" in hits[0]["text"]


def test_rrf_rewards_agreement() -> None:
    dense = [{"text": "A"}, {"text": "B"}, {"text": "C"}]
    lexical = [{"text": "C"}, {"text": "A"}, {"text": "D"}]
    fused = _rrf_fuse(dense, lexical, k=4, rrf_k=60)
    # A is high in both lists -> should win; C (also in both) second.
    assert fused[0]["text"] == "A"
    assert fused[1]["text"] == "C"
    assert "fused_score" in fused[0]


class _FakeStore:
    """A vector store stand-in that counts full-corpus reads."""

    def __init__(self, path, documents):
        self.path = str(path)
        self._documents = list(documents)
        self.generation_value = 1
        self.get_all_calls = 0

    def count(self):
        return len(self._documents)

    def generation(self):
        return self.generation_value

    def get_all(self):
        self.get_all_calls += 1
        return {"documents": self._documents,
                "metadatas": [{"source": f"d{i}.md"} for i in range(len(self._documents))]}

    def edit(self, index, text):
        """Replace a chunk's text without changing the chunk count."""
        self._documents[index] = text
        self.generation_value += 1


def _reset_process_cache():
    lexical_module._cache.clear()


def test_bm25_does_not_reread_the_corpus_on_repeat_queries(tmp_path) -> None:
    """The hot path must not pull every document out of the store per query."""
    _reset_process_cache()
    store = _FakeStore(tmp_path, DOCS)

    for _ in range(5):
        get_bm25(store)

    assert store.get_all_calls == 1


def test_bm25_rebuilds_when_content_changes_but_count_does_not(tmp_path) -> None:
    """A same-size edit must still invalidate — this is why count alone fails."""
    _reset_process_cache()
    store = _FakeStore(tmp_path, DOCS)
    get_bm25(store)

    store.edit(0, "penguins waddle across antarctic ice")
    index = get_bm25(store)

    assert store.get_all_calls == 2
    hits = index.search("penguins antarctic", n=3)
    assert hits and "penguins" in hits[0]["text"]


def test_bm25_disk_cache_survives_a_fresh_process(tmp_path) -> None:
    """A new process reuses the on-disk index instead of rebuilding it."""
    _reset_process_cache()
    store = _FakeStore(tmp_path, DOCS)
    get_bm25(store)
    assert store.get_all_calls == 1

    _reset_process_cache()  # simulates a cold start with a warm disk cache
    index = get_bm25(store)

    assert store.get_all_calls == 1
    assert index.search("quick fox", n=1)[0]["text"] == DOCS[0]


def test_bm25_disk_cache_isolated_between_collections(tmp_path) -> None:
    """Memory and knowledge collections may share a Chroma directory."""
    from rag.chunk import Chunk
    from rag.store import VectorStore

    knowledge = VectorStore(path=str(tmp_path), collection="atelier")
    memory = VectorStore(path=str(tmp_path), collection="atelier_memory")
    chunk = Chunk(text="knowledge alpha", source="knowledge.md", chunk_index=0, metadata={})
    knowledge.add([chunk], [[1.0, 0.0]])
    memory.upsert_raw(["memory-1"], ["memory beta"], [[0.0, 1.0]], [{"kind": "memory"}])
    _reset_process_cache()

    knowledge_index = get_bm25(knowledge)
    memory_index = get_bm25(memory)

    assert knowledge_index.docs == ["knowledge alpha"]
    assert memory_index.docs == ["memory beta"]
    assert knowledge_index is not memory_index
