from atelier.service import AtelierService
from atelier.workspace import WorkspaceManager
from agent.project_memory import ProjectMemoryStore
from atelier.workflow_engine import WorkflowEngine
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


def test_service_supports_source_upload_chat_and_repo_actions(tmp_path):
    service = _service(tmp_path)
    uploaded = service.dispatch("upload", {"filename": "notes.txt", "content": "atelier evidence"})
    assert uploaded["status"] == "success"
    source = service.dispatch("source", {"path": "notes.txt"})
    assert source["content"] == "atelier evidence"
    chat = service.dispatch("chat", {"task": "inspect this repository"})
    assert chat["status"] == "routed"
    repo = service.dispatch("repo_action", {"action": "inspect", "path": "."})
    assert repo["root"] == str((tmp_path / "repo").resolve())


def test_service_can_start_a_workflow_through_task_input(tmp_path):
    base = _service(tmp_path)
    # Rebuild with an isolated workflow and project-memory store for the test.
    engine = WorkflowEngine(manager=base.manager, storage_dir=tmp_path / "workflows")
    service = AtelierService(
        manager=base.manager, registry=base.registry, workflow_engine=engine,
        project_memory=ProjectMemoryStore(tmp_path / "memory.sqlite3"),
    )
    (tmp_path / "repo" / "data.csv").write_text("x\n1\n", encoding="utf-8")
    result = service.dispatch("task_input", {"task": "analyze this CSV dataset", "start": True, "input": {"path": "data.csv"}})
    assert result["workflow"]["status"] == "waiting_approval"
