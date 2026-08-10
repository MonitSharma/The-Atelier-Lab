import json
from urllib.request import Request

import pytest

from atelier.workspace import Workspace, WorkspaceContext, workspace_scope
from tools.research import (
    _AllowlistedRedirectHandler,
    download_paper,
    lookup_research,
    research_graph,
    verify_citation,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class BytesResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit=-1):
        return self.payload if limit < 0 else self.payload[:limit]


def _network_context(tmp_path):
    root = Workspace("research", tmp_path, frozenset({"read", "network"}), "CLOUD_ALLOWED", True)
    return WorkspaceContext(root, (root,))


def test_research_lookup_requires_explicit_network_context(tmp_path):
    result = lookup_research({"query": "quantum optimization"})
    assert result["status"] == "denied"
    assert result["error_type"] == "network_context_required"


def test_crossref_lookup_records_provenance_and_never_reads_local_files(tmp_path):
    payload = {"message": {"items": [{"title": ["A paper"], "DOI": "10.1/test", "URL": "https://doi.org/10.1/test"}]}}

    def opener(request, timeout=20):
        assert "quantum" in request.full_url
        return FakeResponse(payload)

    with workspace_scope(_network_context(tmp_path)):
        result = lookup_research({"source": "crossref", "query": "quantum"}, opener=opener)
    assert result["status"] == "success"
    assert result["source"] == "crossref"
    assert result["records"][0]["doi"] == "10.1/test"
    assert result["request_url"].startswith("https://api.crossref.org/")


def test_research_graph_normalizes_citing_papers(tmp_path):
    payload = {"data": [{"citingPaper": {"paperId": "p1", "title": "Cites it", "authors": [{"name": "A. Author"}], "externalIds": {"DOI": "10.1/citing"}}}]}

    def opener(request, timeout=20):
        assert "/citations?" in request.full_url
        return FakeResponse(payload)

    with workspace_scope(_network_context(tmp_path)):
        result = research_graph({"relation": "cited_by", "paper_id": "seed"}, opener=opener)
    assert result["status"] == "success"
    assert result["records"][0]["doi"] == "10.1/citing"


def test_verify_citation_reports_title_and_author_match(tmp_path):
    payload = {"message": {"title": ["A Verified Paper"], "DOI": "10.1/test", "author": [{"family": "Author"}]}}

    def opener(request, timeout=20):
        return FakeResponse(payload)

    with workspace_scope(_network_context(tmp_path)):
        result = verify_citation({"doi": "10.1/test", "title": "A Verified Paper", "authors": ["Author"]}, opener=opener)
    assert result["status"] == "success"
    assert result["verified"] is True
    assert result["title_similarity"] == 1.0


def test_download_requires_allowlisted_host_and_writes_provenance(tmp_path):
    workspace = Workspace("research", tmp_path, frozenset({"read", "write", "network"}), "CLOUD_ALLOWED", True)
    context = WorkspaceContext(workspace, (workspace,))

    def opener(request, timeout=30):
        assert request.full_url == "https://arxiv.org/pdf/1234.5678"
        return BytesResponse(b"%PDF-test")

    with workspace_scope(context):
        result = download_paper({"url": "https://arxiv.org/pdf/1234.5678", "destination": "paper.pdf"}, opener=opener)
    assert result["status"] == "success"
    assert (tmp_path / "paper.pdf").read_bytes() == b"%PDF-test"
    assert (tmp_path / "paper.pdf.provenance.json").exists()

    with workspace_scope(context):
        denied = download_paper({"url": "https://example.com/paper.pdf", "destination": "other.pdf"}, opener=opener)
    assert denied["error_type"] == "download_host_not_allowed"


def test_download_redirect_cannot_leave_allowlisted_hosts() -> None:
    handler = _AllowlistedRedirectHandler()
    request = Request("https://arxiv.org/pdf/1234.5678")

    with pytest.raises(ValueError, match="redirect target"):
        handler.redirect_request(request, None, 302, "Found", {}, "https://evil.example/payload")
