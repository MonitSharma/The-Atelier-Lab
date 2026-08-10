"""BM25 lexical retrieval over the stored chunks — the keyword arm of hybrid.

Dense (embedding) retrieval is great at meaning but can miss exact terms — a
rare identifier, a specific number, an acronym. BM25 nails those. We build a
compact in-memory BM25 index from the documents already in the vector store
(no extra dependency, no duplicate corpus) and cache it — in memory for the
process, and on disk next to the vector store so a fresh process does not pay
the rebuild either. Both caches are keyed on the store's write generation, so
the corpus is read back only when it has actually changed.
"""

from __future__ import annotations

import math
import pickle
import re
from pathlib import Path
from typing import Any

from rag.store import VectorStore

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, documents: list[str], metadatas: list[dict[str, Any]],
                 k1: float = 1.5, b: float = 0.75) -> None:
        self.docs = documents
        self.metas = metadatas
        self.k1 = k1
        self.b = b
        self.N = len(documents)

        self.tf: list[dict[str, int]] = []
        self.doc_len: list[int] = []
        df: dict[str, int] = {}
        for doc in documents:
            toks = tokenize(doc)
            self.doc_len.append(len(toks))
            counts: dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            self.tf.append(counts)
            for term in counts:
                df[term] = df.get(term, 0) + 1

        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.idf = {
            term: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for term, n in df.items()
        }

    def search(self, query: str, n: int) -> list[dict[str, Any]]:
        q = tokenize(query)
        scored: list[tuple[int, float]] = []
        for i in range(self.N):
            tf = self.tf[i]
            dl = self.doc_len[i] or 1
            s = 0.0
            for term in q:
                f = tf.get(term)
                if not f:
                    continue
                idf = self.idf.get(term, 0.0)
                s += idf * (f * (self.k1 + 1)) / (
                    f + self.k1 * (1 - self.b + self.b * dl / (self.avgdl or 1))
                )
            if s > 0:
                scored.append((i, s))
        scored.sort(key=lambda x: -x[1])
        return [
            {"text": self.docs[i], "metadata": self.metas[i], "score": s, "bm25": s}
            for i, s in scored[:n]
        ]


_cache: dict[str, Any] = {"fingerprint": None, "index": None}


def _fingerprint(store: VectorStore) -> str:
    """Identify the corpus revision without reading the corpus.

    The previous fingerprint pulled every document out of Chroma and SHA-1'd the
    concatenation *on every query* — O(corpus) I/O plus hashing per retrieval,
    which is what made hybrid search degrade as the library grew. The store's
    write generation answers the same question ("has anything changed?") in a
    single small file read, and the chunk count guards against a store whose
    sidecar counter was lost.
    """
    return f"{store.path}:{store.count()}:{store.generation()}"


def _cache_path(store: VectorStore) -> Path:
    return Path(store.path) / "bm25_index.pickle"


def _load_cached(store: VectorStore, fingerprint: str) -> BM25Index | None:
    """Load a previously built index, if it matches the current corpus.

    The cache lives inside the user's own vector-store directory, alongside the
    Chroma database it is derived from, and is only ever written by this
    process — the same trust level as the database itself. A mismatch, a missing
    file, or any unpickling failure simply falls back to rebuilding.
    """
    path = _cache_path(store)
    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, pickle.UnpicklingError, EOFError, AttributeError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("fingerprint") != fingerprint:
        return None
    index = payload.get("index")
    return index if isinstance(index, BM25Index) else None


def _store_cached(store: VectorStore, fingerprint: str, index: BM25Index) -> None:
    path = _cache_path(store)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write-then-rename so a crash mid-write cannot leave a torn cache.
        temporary = path.with_suffix(".pickle.tmp")
        with temporary.open("wb") as handle:
            pickle.dump({"fingerprint": fingerprint, "index": index}, handle,
                        protocol=pickle.HIGHEST_PROTOCOL)
        temporary.replace(path)
    except (OSError, pickle.PicklingError):
        pass  # caching is an optimization; never fail a query over it


def get_bm25(store: VectorStore | None = None) -> BM25Index:
    store = store or VectorStore()
    fingerprint = _fingerprint(store)
    if _cache["index"] is not None and _cache["fingerprint"] == fingerprint:
        return _cache["index"]

    index = _load_cached(store, fingerprint)
    if index is None:
        got = store.get_all()
        index = BM25Index(got.get("documents", []), got.get("metadatas", []))
        _store_cached(store, fingerprint, index)

    _cache["index"] = index
    _cache["fingerprint"] = fingerprint
    return index
