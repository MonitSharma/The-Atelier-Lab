import json

from atelier.workspace import Workspace, WorkspaceContext, workspace_scope
from tools.research import lookup_research


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


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
