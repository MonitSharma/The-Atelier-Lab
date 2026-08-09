"""Explicit, provenance-tracked network research tools.

These tools accept only an explicit query or DOI. They never read local files
or turn local document contents into an external request. Network access is
checked against the active workspace before an HTTP request is made.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from collections.abc import Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from typing import Any

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


def _http_json(url: str, opener: _OPEN | None = None) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Atelier/1.0"})
    with (opener or urlopen)(request, timeout=20) as response:  # noqa: S310 - URL is fixed below
        return json.loads(response.read().decode("utf-8"))


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
