"""Explicit, provenance-tracked network research tools.

These tools accept only an explicit query or DOI. They never read local files
or turn local document contents into an external request. Network access is
checked against the active workspace before an HTTP request is made.
"""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from datetime import UTC, datetime
from collections.abc import Callable
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from typing import Any

from atelier.config import settings

from atelier.workspace import WorkspaceError, current_workspace_context
from tools.base import Tool

_OPEN = Callable[[Request], Any]


def _network_error() -> dict[str, Any] | None:
    context = current_workspace_context()
    if context is None:
        return {"status": "denied", "error_type": "network_context_required",
                "message": "Research tools require an explicit workspace context."}
    try:
        context.require_network()
    except WorkspaceError as exc:
        return {"status": "denied", "error_type": "network_denied", "message": str(exc)}
    return None


def _cache_path(url: str) -> Path:
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return settings.research_cache_dir / f"{key}.json"


def _cached_json(url: str, ttl_seconds: int) -> dict[str, Any] | None:
    path = _cache_path(url)
    try:
        if (datetime.now(UTC).timestamp() - path.stat().st_mtime) > ttl_seconds:
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload.get("response") if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _write_cache(url: str, response: dict[str, Any]) -> None:
    settings.research_cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(url)
    path.write_text(json.dumps({"url": url, "cached_at": datetime.now(UTC).isoformat(), "response": response}), encoding="utf-8")


def _http_json(url: str, opener: _OPEN | None = None, *, cache_ttl: int = 86_400) -> dict[str, Any]:
    if opener is None:
        cached = _cached_json(url, cache_ttl)
        if cached is not None:
            return cached
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Atelier/1.0"})
    with (opener or urlopen)(request, timeout=20) as response:  # noqa: S310 - URL is fixed below
        payload = json.loads(response.read().decode("utf-8"))
    if opener is None:
        _write_cache(url, payload)
    return payload


def _crossref(query: str, max_results: int, opener: _OPEN | None = None) -> list[dict[str, Any]]:
    params = urlencode({"query.bibliographic": query, "rows": max_results})
    payload = _http_json(f"https://api.crossref.org/works?{params}", opener)
    records = []
    for item in payload.get("message", {}).get("items", [])[:max_results]:
        records.append({
            "title": (item.get("title") or [""])[0],
            "doi": item.get("DOI"),
            "url": item.get("URL"),
            "published": item.get("published-print") or item.get("published-online"),
            "authors": [a.get("family") for a in item.get("author", []) if a.get("family")],
            "container": item.get("container-title", [""])[0],
        })
    return records


def _crossref_doi(doi: str, opener: _OPEN | None = None) -> list[dict[str, Any]]:
    payload = _http_json(f"https://api.crossref.org/works/{quote(doi, safe='')}", opener)
    item = payload.get("message", {})
    return _crossref_item(item)


def _crossref_item(item: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "title": (item.get("title") or [""])[0],
        "doi": item.get("DOI"),
        "url": item.get("URL"),
        "published": item.get("published-print") or item.get("published-online"),
        "authors": [a.get("family") for a in item.get("author", []) if a.get("family")],
        "container": item.get("container-title", [""])[0],
    }]


def _arxiv(query: str, max_results: int, opener: _OPEN | None = None) -> list[dict[str, Any]]:
    params = urlencode({"search_query": f"all:{query}", "start": 0, "max_results": max_results})
    request = Request(
        f"https://export.arxiv.org/api/query?{params}",
        headers={"Accept": "application/atom+xml", "User-Agent": "Atelier/1.0"},
    )
    with (opener or urlopen)(request, timeout=20) as response:  # noqa: S310 - fixed host
        root = ElementTree.fromstring(response.read())
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    records = []
    for entry in root.findall("atom:entry", ns)[:max_results]:
        records.append({
            "title": " ".join((entry.findtext("atom:title", "", ns) or "").split()),
            "summary": " ".join((entry.findtext("atom:summary", "", ns) or "").split())[:1000],
            "url": entry.findtext("atom:id", "", ns),
            "published": entry.findtext("atom:published", "", ns),
            "authors": [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)],
        })
    return records


def _semantic_scholar(query: str, max_results: int, opener: _OPEN | None = None) -> list[dict[str, Any]]:
    params = urlencode({"query": query, "limit": max_results, "fields": "title,authors,year,abstract,url,externalIds"})
    payload = _http_json(f"https://api.semanticscholar.org/graph/v1/paper/search?{params}", opener)
    records = []
    for item in payload.get("data", [])[:max_results]:
        records.append({
            "title": item.get("title", ""), "abstract": item.get("abstract"),
            "year": item.get("year"), "url": item.get("url"),
            "doi": (item.get("externalIds") or {}).get("DOI"),
            "authors": [a.get("name") for a in item.get("authors", []) if a.get("name")],
        })
    return records


def lookup_research(arguments: dict[str, Any], *, opener: _OPEN | None = None) -> dict[str, Any]:
    denied = _network_error()
    if denied:
        return denied
    source = arguments.get("source", "crossref")
    query = arguments.get("query")
    doi = arguments.get("doi")
    if source not in {"crossref", "arxiv", "semantic_scholar"}:
        return {"status": "error", "error_type": "invalid_source", "message": "Use crossref, arxiv, or semantic_scholar."}
    if not isinstance(query, str) or not query.strip():
        if not isinstance(doi, str) or not doi.strip() or source != "crossref":
            return {"status": "error", "error_type": "invalid_arguments", "message": "Provide an explicit query, or a Crossref DOI."}
    max_results = arguments.get("max_results", 5)
    if not isinstance(max_results, int) or not 1 <= max_results <= 20:
        max_results = 5
    query = query.strip() if isinstance(query, str) else ""
    try:
        if doi and source == "crossref":
            records = _crossref_doi(str(doi).strip(), opener)
            request_url = f"https://api.crossref.org/works/{quote(str(doi).strip(), safe='')}"
        elif source == "crossref":
            records = _crossref(query, max_results, opener)
            request_url = "https://api.crossref.org/works"
        elif source == "arxiv":
            records = _arxiv(query, max_results, opener)
            request_url = "https://export.arxiv.org/api/query"
        else:
            records = _semantic_scholar(query, max_results, opener)
            request_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    except Exception as exc:  # noqa: BLE001 - return a structured tool result
        return {"status": "error", "error_type": "research_request_failed", "message": str(exc)}
    return {
        "status": "success", "tool": "research_lookup", "source": source,
        "query": query or None, "doi": doi or None, "retrieved_at": datetime.now(UTC).isoformat(),
        "request_url": request_url, "records": records,
    }


def _semantic_paper_id(arguments: dict[str, Any]) -> str | None:
    paper_id = arguments.get("paper_id")
    doi = arguments.get("doi")
    if isinstance(paper_id, str) and paper_id.strip():
        return paper_id.strip()
    if isinstance(doi, str) and doi.strip():
        return f"DOI:{doi.strip()}"
    return None


def _semantic_paper(item: dict[str, Any]) -> dict[str, Any]:
    external = item.get("externalIds") or {}
    return {
        "paper_id": item.get("paperId"),
        "title": item.get("title", ""),
        "abstract": item.get("abstract"),
        "year": item.get("year"),
        "url": item.get("url"),
        "doi": external.get("DOI"),
        "authors": [a.get("name") for a in item.get("authors", []) if a.get("name")],
    }


def research_graph(arguments: dict[str, Any], *, opener: _OPEN | None = None) -> dict[str, Any]:
    """Return related papers or papers citing an explicit Semantic Scholar id."""
    denied = _network_error()
    if denied:
        return denied
    relation = arguments.get("relation", "related")
    if relation not in {"related", "cited_by"}:
        return {"status": "error", "error_type": "invalid_relation", "message": "Use related or cited_by."}
    paper_id = _semantic_paper_id(arguments)
    if paper_id is None:
        return {"status": "error", "error_type": "invalid_arguments", "message": "Provide paper_id or doi."}
    limit = arguments.get("max_results", 10)
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        limit = 10
    fields = "title,authors,year,abstract,url,externalIds,paperId"
    endpoint = "recommended" if relation == "related" else "citations"
    params = urlencode({"limit": limit, "fields": fields})
    url = f"https://api.semanticscholar.org/graph/v1/paper/{quote(paper_id, safe=':')}/{endpoint}?{params}"
    try:
        payload = _http_json(url, opener)
    except Exception as exc:  # noqa: BLE001 - return structured tool result
        return {"status": "error", "error_type": "research_request_failed", "message": str(exc)}
    records = []
    for item in payload.get("data", [])[:limit]:
        candidate = item.get("citingPaper", item) if relation == "cited_by" else item
        if isinstance(candidate, dict):
            records.append(_semantic_paper(candidate))
    return {"status": "success", "tool": "research_graph", "relation": relation,
            "paper_id": paper_id, "request_url": url,
            "retrieved_at": datetime.now(UTC).isoformat(), "records": records}


def verify_citation(arguments: dict[str, Any], *, opener: _OPEN | None = None) -> dict[str, Any]:
    """Compare an explicit citation against Crossref metadata without guessing."""
    denied = _network_error()
    if denied:
        return denied
    doi = arguments.get("doi")
    expected_title = arguments.get("title")
    expected_authors = arguments.get("authors", [])
    if not isinstance(doi, str) or not doi.strip() or not isinstance(expected_title, str) or not expected_title.strip():
        return {"status": "error", "error_type": "invalid_arguments", "message": "Provide doi and title."}
    try:
        records = _crossref_doi(doi.strip(), opener)
    except Exception as exc:  # noqa: BLE001 - return structured tool result
        return {"status": "error", "error_type": "research_request_failed", "message": str(exc)}
    actual = records[0] if records else {}
    def normalize(value: object) -> str:
        return "".join(ch.lower() for ch in str(value) if ch.isalnum())
    title_score = SequenceMatcher(None, normalize(expected_title), normalize(actual.get("title", ""))).ratio()
    expected_names = {normalize(name) for name in expected_authors if isinstance(name, str)}
    actual_names = {normalize(name) for name in actual.get("authors", [])}
    author_overlap = len(expected_names & actual_names) / max(1, len(expected_names)) if expected_names else None
    verified = title_score >= 0.92 and (author_overlap is None or author_overlap >= 0.5)
    return {"status": "success", "tool": "verify_citation", "verified": verified,
            "doi": doi.strip(), "expected_title": expected_title,
            "title_similarity": round(title_score, 4), "author_overlap": author_overlap,
            "crossref": actual, "retrieved_at": datetime.now(UTC).isoformat()}


_DOWNLOAD_HOSTS = frozenset({"arxiv.org", "export.arxiv.org", "doi.org", "api.crossref.org"})


def download_paper(arguments: dict[str, Any], *, opener: _OPEN | None = None) -> dict[str, Any]:
    """Download an explicitly selected paper URL into the approved workspace."""
    denied = _network_error()
    if denied:
        return denied
    url = arguments.get("url")
    destination = arguments.get("destination")
    if not isinstance(url, str) or not isinstance(destination, str) or not url.strip() or not destination.strip():
        return {"status": "error", "error_type": "invalid_arguments", "message": "Provide url and destination."}
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _DOWNLOAD_HOSTS:
        return {"status": "denied", "error_type": "download_host_not_allowed", "message": "Only approved HTTPS research hosts may be downloaded."}
    context = current_workspace_context()
    if context is None:
        return {"status": "denied", "error_type": "network_context_required", "message": "Downloads require an explicit workspace context."}
    try:
        resolved = context.resolve(destination, "write")
        context.require_network(resolved.workspace)
    except WorkspaceError as exc:
        return {"status": "denied", "error_type": "workspace_denied", "message": str(exc)}
    target = resolved.path
    if target.exists() and not bool(arguments.get("overwrite", False)):
        return {"status": "error", "error_type": "destination_exists", "message": str(target)}
    max_bytes = arguments.get("max_bytes", 50_000_000)
    if not isinstance(max_bytes, int) or not 1 <= max_bytes <= 50_000_000:
        max_bytes = 50_000_000
    try:
        request = Request(url, headers={"Accept": "application/pdf,application/octet-stream", "User-Agent": "Atelier/1.0"})
        with (opener or urlopen)(request, timeout=30) as response:  # noqa: S310 - host allowlist above
            content = response.read(max_bytes + 1)
        if len(content) > max_bytes:
            return {"status": "error", "error_type": "download_too_large", "message": f"Maximum is {max_bytes} bytes."}
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        provenance = target.with_name(f"{target.name}.provenance.json")
        provenance.write_text(json.dumps({"url": url, "downloaded_at": datetime.now(UTC).isoformat(), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - return structured tool result
        return {"status": "error", "error_type": "download_failed", "message": str(exc)}
    return {"status": "success", "tool": "download_paper", "path": str(target),
            "provenance": str(provenance), "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "url": url}


def run_research_lookup(arguments: dict[str, Any]) -> dict[str, Any]:
    return lookup_research(arguments)


RESEARCH_LOOKUP_TOOL = Tool(
    name="research_lookup",
    description=(
        "Look up explicit paper metadata from Crossref, arXiv, or Semantic Scholar. "
        "Networked and provenance-tracked; never sends local file contents."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "source": {"type": "string", "enum": ["crossref", "arxiv", "semantic_scholar"]},
            "query": {"type": "string"}, "doi": {"type": "string"},
            "max_results": {"type": "integer", "minimum": 1, "maximum": 20},
        },
        "additionalProperties": False,
    },
    function=run_research_lookup,
)


RESEARCH_GRAPH_TOOL = Tool(
    name="research_graph",
    description="Find related papers or papers citing an explicit Semantic Scholar paper id or DOI.",
    input_schema={"type": "object", "properties": {
        "relation": {"type": "string", "enum": ["related", "cited_by"]},
        "paper_id": {"type": "string"}, "doi": {"type": "string"},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 100}},
        "additionalProperties": False},
    function=lambda arguments: research_graph(arguments),
)

VERIFY_CITATION_TOOL = Tool(
    name="verify_citation",
    description="Verify an explicit DOI citation against Crossref title and author metadata.",
    input_schema={"type": "object", "required": ["doi", "title"], "properties": {
        "doi": {"type": "string"}, "title": {"type": "string"},
        "authors": {"type": "array", "items": {"type": "string"}}},
        "additionalProperties": False},
    function=lambda arguments: verify_citation(arguments),
)

DOWNLOAD_PAPER_TOOL = Tool(
    name="download_paper",
    description="Download an explicitly selected HTTPS paper URL into an approved CLOUD_ALLOWED workspace with provenance.",
    input_schema={"type": "object", "required": ["url", "destination"], "properties": {
        "url": {"type": "string"}, "destination": {"type": "string"},
        "overwrite": {"type": "boolean"}, "max_bytes": {"type": "integer"}},
        "additionalProperties": False},
    function=lambda arguments: download_paper(arguments),
)
