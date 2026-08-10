import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from atelier.api import _Handler
from atelier.service import AtelierService
from atelier.workspace import WorkspaceManager


@pytest.fixture
def api_server(tmp_path: Path):
    """A running loopback API bound to an ephemeral port."""
    root = tmp_path / "repo"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="repo", capabilities={"read", "write", "execute"})
    manager.open("repo")
    if "atelier" in {item.name for item in manager.list()}:
        manager.close("atelier")
    handler = type("TestAtelierHandler", (_Handler,), {"service": AtelierService(manager=manager)})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _post(base: str, path: str, body: dict, **headers: str) -> Request:
    return Request(
        base + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )


def test_cross_origin_post_is_rejected(api_server: str):
    """A page on another origin must not be able to drive the local API."""
    request = _post(api_server, "/route", {"task": "x"}, Origin="http://evil.example")
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)
    assert excinfo.value.code == 403
    assert json.loads(excinfo.value.read())["error_type"] == "cross_origin_denied"


def test_cross_site_fetch_metadata_is_rejected(api_server: str):
    request = _post(api_server, "/route", {"task": "x"})
    request.add_header("Sec-Fetch-Site", "cross-site")
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)
    assert excinfo.value.code == 403


def test_non_loopback_host_header_is_rejected(api_server: str):
    """DNS rebinding arrives with an attacker-controlled Host it cannot forge."""
    request = Request(api_server + "/health", headers={"Host": "attacker.example"})
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)
    assert excinfo.value.code == 403
    assert json.loads(excinfo.value.read())["error_type"] == "untrusted_host"


def test_simple_request_content_type_is_rejected(api_server: str):
    """`text/plain` is the CSRF-relevant case: it needs no CORS preflight."""
    request = Request(
        api_server + "/route",
        data=json.dumps({"task": "x"}).encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        method="POST",
    )
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)
    assert excinfo.value.code == 415


def test_cors_preflight_is_refused(api_server: str):
    request = Request(api_server + "/route", method="OPTIONS")
    with pytest.raises(HTTPError) as excinfo:
        urlopen(request)
    assert excinfo.value.code == 405
    assert "Access-Control-Allow-Origin" not in excinfo.value.headers


def test_same_origin_ui_requests_still_work(api_server: str):
    """The bundled UI is same-origin, so nothing above should impede it."""
    request = _post(api_server, "/route", {"task": "inspect this repository"},
                    Origin=api_server)
    with urlopen(request) as response:
        assert json.loads(response.read())["workflow"] == "code_fix"


def test_loopback_api_uses_the_shared_service_contract(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="repo", capabilities={"read", "write", "execute"})
    manager.open("repo")
    if "atelier" in {item.name for item in manager.list()}:
        manager.close("atelier")
    service = AtelierService(manager=manager)
    handler = type("TestAtelierHandler", (_Handler,), {"service": service})
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(base + "/health") as response:
            health = json.loads(response.read())
        assert health["status"] == "ok"

        with urlopen(base + "/ui") as response:
            page = response.read().decode("utf-8")
        assert "Atelier Workbench" in page

        request = Request(
            base + "/route",
            data=json.dumps({"task": "inspect this repository"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request) as response:
            routed = json.loads(response.read())
        assert routed["domain"] == "code"
        assert routed["workflow"] == "code_fix"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
