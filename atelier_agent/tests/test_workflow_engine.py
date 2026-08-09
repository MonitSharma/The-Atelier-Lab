import json

from atelier.service import AtelierService
from agent.project_memory import ProjectMemoryStore
from atelier.workflow_engine import WorkflowEngine
from atelier.workspace import WorkspaceManager


def _engine(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="workspace", capabilities={"read", "write", "execute"})
    manager.open("workspace")
    if "atelier" in {item.name for item in manager.list()}:
        manager.close("atelier")
    return WorkflowEngine(manager=manager, storage_dir=tmp_path / "workflows"), manager, root


def test_repo_workflow_persists_checkpoints_and_evidence(tmp_path):
    engine, manager, root = _engine(tmp_path)
    (root / "README.md").write_text("# Example\n", encoding="utf-8")
    state = engine.start("repo_inspect", {"path": "."})

    assert state.status == "completed"
    assert len(state.checkpoints) == 4
    assert len(state.evidence) == 4
    persisted = json.loads((tmp_path / "workflows" / f"{state.run_id}.json").read_text())
    assert persisted["status"] == "completed"
    assert engine.get(state.run_id).run_id == state.run_id


def test_approval_gate_can_pause_and_resume_data_workflow(tmp_path):
    engine, _, root = _engine(tmp_path)
    (root / "data.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    state = engine.start("data_analyze", {"path": "data.csv"})

    assert state.status == "waiting_approval"
    assert state.approval_required == "summarize"
    resumed = engine.approve(state.run_id)
    assert resumed.status == "completed"
    assert resumed.approved is True


def test_failed_workflow_recovers_from_checkpoint(tmp_path):
    engine, _, root = _engine(tmp_path)
    state = engine.start("data_analyze", {"path": "missing.csv"})
    assert state.status == "failed"
    (root / "missing.csv").write_text("x\n1\n", encoding="utf-8")

    recovered = engine.recover(state.run_id)
    assert recovered.status == "waiting_approval"
    assert recovered.step_index == 2


def test_service_exposes_workflow_and_task_operations(tmp_path):
    engine, manager, root = _engine(tmp_path)
    (root / "data.json").write_text("{\"ok\": true}\n", encoding="utf-8")
    service = AtelierService(manager=manager, workflow_engine=engine, project_memory=ProjectMemoryStore(tmp_path / "project-memory.sqlite3"))
    started = service.dispatch("task_create", {"workflow": "data_analyze", "input": {"path": "data.json"}})
    assert started["status"] == "waiting_approval"
    listed = service.dispatch("tasks")["tasks"]
    assert any(item["run_id"] == started["run_id"] for item in listed)
    approved = service.dispatch("task_approve", {"run_id": started["run_id"]})
    assert approved["status"] == "completed"
