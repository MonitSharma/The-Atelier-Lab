"""BM25 lexical retrieval over the stored chunks — the keyword arm of hybrid.

Dense (embedding) retrieval is great at meaning but can miss exact terms — a
rare identifier, a specific number, an acronym. BM25 nails those. We build a
compact in-memory BM25 index from the documents already in the vector store
(no extra dependency, no duplicate corpus) and cache it, rebuilding only when
the store's chunk count changes.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

from atelier.config import settings
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


def get_bm25(store: VectorStore | None = None) -> BM25Index:
    store = store or VectorStore()
    got = store.get_all()
    documents = got.get("documents", [])
    fingerprint = hashlib.sha1("\0".join(documents).encode("utf-8")).hexdigest()
    if _cache["index"] is None or _cache["fingerprint"] != fingerprint:
        _cache["index"] = BM25Index(got.get("documents", []), got.get("metadatas", []))
        _cache["fingerprint"] = fingerprint
    return _cache["index"]
