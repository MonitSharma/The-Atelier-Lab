"""Retrieval: embed a query, fetch nearest chunks, format them for the prompt."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
from typing import Any

from atelier.config import settings
from rag.embed import get_embedder
from rag.store import VectorStore

REFERENCE_TERMS = {
    "reference", "references", "bibliography", "citation", "citations", "cited",
    "papers", "prior", "related", "literature", "sources",
}
RECENCY_TERMS = {
    "recent", "recently", "latest", "newest", "new", "today", "todays",
    "yesterday", "current", "currently", "thisweek", "thismonth", "up-to-date",
    "uptodate",
}
RECENCY_QUERY_FILLER = {
    "a", "an", "are", "about", "all", "and", "any", "give", "in", "information",
    "me", "news", "of", "on", "show", "the", "these", "this", "updates", "update",
    "what", "which", "with",
}
SOURCE_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-_.](\d{1,2})[-_.](\d{1,2})(?!\d)")


def reference_intent(query: str) -> bool:
    return bool(REFERENCE_TERMS.intersection(query.lower().split()))


def recency_intent(query: str) -> bool:
    """Return whether the user explicitly asks for time-sensitive material."""
    normalized = re.sub(r"[^a-z0-9]+", " ", query.lower()).split()
    compact = "".join(normalized)
    return bool(set(normalized).intersection(RECENCY_TERMS) or compact in RECENCY_TERMS)


def source_date(metadata: dict[str, Any]) -> date | None:
    """Extract a publication/update date from metadata or a dated filename."""
    for key in ("source_date", "publication_date", "document_date", "date"):
        value = metadata.get(key)
        if value:
            try:
                return date.fromisoformat(str(value)[:10])
            except ValueError:
                pass
    source = str(metadata.get("source", metadata.get("filename", "")))
    match = SOURCE_DATE_RE.search(Path(source).name)
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _source_query_terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    return [
        token for token in tokens
        if len(token) >= 3 and token not in RECENCY_TERMS and token not in RECENCY_QUERY_FILLER
    ]


def _source_matches_query(metadata: dict[str, Any], query: str) -> bool:
    """Limit date-based expansion to sources named by the user's domain term."""
    terms = _source_query_terms(query)
    if not terms:
        return True
    source = str(metadata.get("source", metadata.get("filename", ""))).lower()
    return any(term in source for term in terms)


def _recent_candidates(store: VectorStore, query: str, limit: int) -> list[dict[str, Any]]:
    """Add one semantically useful chunk from each of the newest dated sources.

    A normal vector query can miss a new document when older documents have
    stronger semantic similarity. Recency queries therefore inspect the stored
    source metadata as a second retrieval arm. This is intentionally activated
    only for explicit time-sensitive language.
    """
    payload = store.get_all()
    documents = payload.get("documents", [])
    metadatas = payload.get("metadatas", [])
    groups: dict[str, list[tuple[str, dict[str, Any], date]]] = {}
    terms = _source_query_terms(query)
    for text, metadata in zip(documents, metadatas):
        metadata = dict(metadata or {})
        published = source_date(metadata)
        if published is None or not _source_matches_query(metadata, query):
            continue
        source = str(metadata.get("source", metadata.get("filename", "?")))
        groups.setdefault(source, []).append((text, metadata, published))

    ordered_sources = sorted(
        groups.items(),
        key=lambda item: max(row[2] for row in item[1]),
        reverse=True,
    )
    recent: list[dict[str, Any]] = []
    for _source, rows in ordered_sources[:limit]:
        rows.sort(
            key=lambda row: sum(row[0].lower().count(term) for term in terms),
            reverse=True,
        )
        text, metadata, published = rows[0]
        metadata["source_date"] = published.isoformat()
        recent.append({
            "text": text,
            "metadata": metadata,
            "score": 0.0,
            "fused_score": 0.0,
            "recency_candidate": True,
        })
    return recent


def _rrf_fuse(
    dense: list[dict[str, Any]],
    lexical: list[dict[str, Any]],
    k: int,
    rrf_k: int,
) -> list[dict[str, Any]]:
    """Reciprocal Rank Fusion: combine two ranked lists by rank, not by score.

    RRF is robust precisely because it ignores the (incomparable) raw scores of
    dense vs. BM25 and uses only positions: score = sum 1/(rrf_k + rank).
    """
    table: dict[str, dict[str, Any]] = {}
    for rank, hit in enumerate(dense):
        entry = table.setdefault(hit["text"], {"hit": hit, "score": 0.0})
        entry["score"] += 1.0 / (rrf_k + rank)
    for rank, hit in enumerate(lexical):
        entry = table.setdefault(hit["text"], {"hit": hit, "score": 0.0})
        entry["score"] += 1.0 / (rrf_k + rank)
    fused = sorted(table.values(), key=lambda e: -e["score"])
    out: list[dict[str, Any]] = []
    for entry in fused[:k]:
        hit = dict(entry["hit"])
        hit["fused_score"] = round(entry["score"], 5)
        out.append(hit)
    return out


def _section_adjustment(hit: dict[str, Any], *, wants_references: bool) -> float:
    section = hit.get("metadata", {}).get("section_type", "other")
    if wants_references:
        return {"references": 1.12, "related_work": 1.08}.get(section, 1.0)
    if section == "references":
        # References remain searchable, but broad concept queries should not
        # let citation lists outrank substantive sections across the corpus.
        return 0.35
    if section in {"abstract", "introduction", "methods", "theory", "experiments", "results", "discussion", "conclusion", "related_work"}:
        return 1.04
    return 1.0


def _post_rank(candidates: list[dict[str, Any]], query: str, k: int) -> list[dict[str, Any]]:
    wants_references = reference_intent(query)
    wants_recent = recency_intent(query)
    scored: list[dict[str, Any]] = []
    for hit in candidates:
        item = dict(hit)
        item["metadata"] = dict(item.get("metadata", {}))
        published = source_date(item["metadata"])
        if published is not None:
            item["metadata"].setdefault("source_date", published.isoformat())
            item["source_date"] = published.isoformat()
        base = float(item.get("fused_score", item.get("score", 0.0)))
        adjustment = _section_adjustment(item, wants_references=wants_references)
        item["section_adjustment"] = adjustment
        item["final_score"] = round(base * adjustment, 8)
        scored.append(item)
    if wants_recent:
        # For explicit recency questions, date is the primary ranking signal;
        # semantic relevance remains the tie-breaker. Undated material is last.
        scored.sort(
            key=lambda hit: (
                source_date(hit["metadata"]) is None,
                -(source_date(hit["metadata"]).toordinal() if source_date(hit["metadata"]) else 0),
                -hit["final_score"],
            )
        )
    else:
        scored.sort(key=lambda hit: -hit["final_score"])

    selected: list[dict[str, Any]] = []
    seen_pairs: dict[tuple[str, str], int] = {}
    deferred: list[dict[str, Any]] = []
    for hit in scored:
        meta = hit.get("metadata", {})
        if wants_recent and source_date(meta) is not None:
            pair = (str(meta.get("document_id", meta.get("source", "?"))), "recent_source")
        else:
            pair = (str(meta.get("document_id", meta.get("source", "?"))), str(meta.get("section_type", "other")))
        if seen_pairs.get(pair, 0) >= 1:
            deferred.append(hit)
            continue
        selected.append(hit)
        seen_pairs[pair] = seen_pairs.get(pair, 0) + 1
        if len(selected) >= k:
            return selected
    selected.extend(deferred[: max(0, k - len(selected))])
    return selected[:k]


def retrieve(
    query: str,
    k: int | None = None,
    store: VectorStore | None = None,
    *,
    hybrid: bool | None = None,
    rerank: bool | None = None,
    source: str | None = None,
    section_type: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve the top-k chunks for a query.

    Pipeline: dense (always) [+ BM25 fused via RRF if hybrid] [→ cross-encoder
    rerank if enabled]. Defaults come from config; pass explicit flags to override.
    """
    store = store or VectorStore()
    k = k or settings.retrieval_k
    use_hybrid = settings.use_hybrid if hybrid is None else hybrid
    do_rerank = settings.rerank if rerank is None else rerank

    n = max(settings.hybrid_candidates, k)
    pool = n

    from rag.compat import ensure_compatible
    from rag.manifest import IndexManifest

    ensure_compatible(store, IndexManifest(), get_embedder())

    dense = store.query(get_embedder().embed_query(query), k=n)
    if source or section_type:
        dense = [hit for hit in dense if (
            not source or Path(hit["metadata"].get("source", "")).name == Path(source).name
        ) and (not section_type or hit["metadata"].get("section_type") == section_type)]
    if use_hybrid:
        from rag.lexical import get_bm25

        lexical = get_bm25(store).search(query, n)
        lexical = [hit for hit in lexical if (
            not source or Path(hit["metadata"].get("source", "")).name == Path(source).name
        ) and (not section_type or hit["metadata"].get("section_type") == section_type)]
        candidates = _rrf_fuse(dense, lexical, pool, settings.rrf_k)
    else:
        candidates = dense[:pool]

    if recency_intent(query):
        existing = {(
            str(hit.get("metadata", {}).get("source", "")), hit.get("text", "")
        ) for hit in candidates}
        for hit in _recent_candidates(store, query, limit=max(k, settings.retrieval_k)):
            key = (str(hit["metadata"].get("source", "")), hit.get("text", ""))
            if key not in existing:
                candidates.append(hit)
                existing.add(key)

    if do_rerank and candidates:
        from rag.rerank import rerank as _do_rerank

        candidates = _do_rerank(query, candidates, len(candidates) if recency_intent(query) else k)

    return _post_rank(candidates, query, k)


def format_context(hits: list[dict[str, Any]], max_chars: int | None = None) -> str:
    """Render retrieved chunks into a numbered, citable context block."""
    max_chars = max_chars or settings.max_context_chars
    blocks: list[str] = []
    used = 0
    for i, hit in enumerate(hits, start=1):
        src = hit["metadata"].get("source", "?")
        name = Path(src).name if src != "?" else "?"
        meta = hit["metadata"]
        location: list[str] = []
        if meta.get("page") is not None:
            location.append(f"p. {meta['page']}")
        if meta.get("source_date"):
            location.append(f"date: {meta['source_date']}")
        if meta.get("slide") is not None:
            location.append(f"slide {meta['slide']}")
        if meta.get("heading"):
            location.append(f"heading: {meta['heading']}")
        if meta.get("section"):
            location.append(f"section: {meta['section']}")
        if meta.get("table") is not None:
            location.append(f"table {meta['table']}")
        if meta.get("speaker_notes"):
            location.append("speaker notes")
        if meta.get("image_member"):
            location.append(f"image: {meta['image_member']}")
        if meta.get("archive_member"):
            location.append(f"archive: {meta['archive_member']}")
        if meta.get("human_review"):
            location.append("HUMAN REVIEW FLAG")
        header = f"[{i}] {name}" + (f"  ({'; '.join(location)})" if location else "")
        body = hit["text"]
        block = f"{header}\n{body}"
        if used + len(block) > max_chars and blocks:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n---\n\n".join(blocks)


def citations(hits: list[dict[str, Any]]) -> list[str]:
    """De-duplicated source-location citations for display under an answer."""
    seen: list[str] = []
    for hit in hits:
        meta = hit["metadata"]
        name = Path(meta.get("source", "?")).name
        location: list[str] = []
        if meta.get("page") is not None:
            location.append(f"p. {meta['page']}")
        if meta.get("slide") is not None:
            location.append(f"slide {meta['slide']}")
        if meta.get("table") is not None:
            location.append(f"table {meta['table']}")
        if meta.get("archive_member"):
            location.append(f"archive:{meta['archive_member']}")
        label = f"{name} ({'; '.join(location)})" if location else name
        if label not in seen:
            seen.append(label)
    return seen
