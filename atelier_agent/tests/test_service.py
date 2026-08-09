from atelier.service import AtelierService
from atelier.workspace import WorkspaceManager
from tools.registry import create_default_registry


def _service(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="repo", capabilities={"read", "write", "execute"})
    manager.open("repo")
    manager.close("atelier")
    return AtelierService(manager=manager, registry=create_default_registry(workspace=manager.context()))


def test_service_dispatches_shared_operations(tmp_path):
    service = _service(tmp_path)
    assert service.dispatch("health")["status"] == "ok"
    assert service.dispatch("workflows")["workflows"]
    result = service.dispatch("tool", {"name": "calculator", "arguments": {"expression": "6*7"}})
    assert result["result"] == 42


def test_service_rejects_unknown_operation(tmp_path):
    result = _service(tmp_path).dispatch("not-real")
    assert result["error_type"] == "unknown_operation"
