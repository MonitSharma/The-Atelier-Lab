import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from atelier.api import _Handler
from atelier.service import AtelierService
from atelier.workspace import WorkspaceManager


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
