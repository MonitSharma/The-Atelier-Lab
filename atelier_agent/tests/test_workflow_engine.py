import json

import pytest

from agent.project_memory import ProjectMemoryStore
from atelier.service import AtelierService
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


def _network_engine(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="workspace", capabilities={"read", "network"}, privacy="CLOUD_ALLOWED")
    manager.open("workspace")
    if "atelier" in {item.name for item in manager.list()}:
        manager.close("atelier")
    return WorkflowEngine(manager=manager, storage_dir=tmp_path / "workflows"), manager


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


def test_workflow_retention_is_dry_run_first(tmp_path):
    from atelier.workflow_retention import retention_candidates

    workflow_dir = tmp_path / "workflows"
    workflow_dir.mkdir()
    (workflow_dir / "old.json").write_text(json.dumps({
        "run_id": "old", "workflow": "research_deep", "status": "failed",
        "updated_at": "2020-01-01T00:00:00Z",
    }))

    candidates = retention_candidates(workflow_dir, keep_successful=0, failed_days=0)
    assert [item["run_id"] for item in candidates] == ["old"]
    assert (workflow_dir / "old.json").exists()


def test_figure_workflow_persists_page_evidence_before_interpretation(tmp_path):
    fitz = pytest.importorskip("fitz")
    engine, _, root = _engine(tmp_path)
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Figure 1: Acceptance workflow\n" + "scientific evidence " * 20)
    paper = root / "figure.pdf"
    document.save(paper)
    document.close()

    state = engine.start("figure_inspect", {"path": "figure.pdf"})
    assert state.status == "waiting_approval"
    assert state.approval_required == "interpret visual"
    assert state.outputs["locate pages"]["figure_pages"] == [1]

    resumed = engine.approve(state.run_id)
    assert resumed.status == "completed"
    assert resumed.outputs["cite pages"]["status"] == "ready"


def test_deep_research_workflow_persists_iterative_report(tmp_path, monkeypatch):
    def fake_lookup(arguments):
            query = arguments["query"].replace(" ", "-")
            provider = arguments["source"]
            return {"status": "success", "records": [{
                "title": f"{provider} {query}", "doi": f"10.1/{provider}.{query}",
                "summary": "Bounded research evidence.", "year": 2026,
            }]}

    monkeypatch.setattr("agent.research_workflow.lookup_research", fake_lookup)
    engine, manager = _network_engine(tmp_path)
    service = AtelierService(
        manager=manager,
        workflow_engine=engine,
        project_memory=ProjectMemoryStore(tmp_path / "project-memory.sqlite3"),
    )
    state = service.dispatch("research_deep", {
        "question": "How does bounded research work?",
        "depth": "standard",
        "sources": ["crossref"],
        "model_free": True,
    })

    assert state["status"] == "completed"
    assert len(state["checkpoints"]) == 5
    assert state["outputs"]["search and iterate"]["rounds"]
    assert state["outputs"]["verify report"]["citation_integrity"] is True
    assert "# Research answer" in state["outputs"]["verify report"]["report_markdown"]
    assert "Research trace" in state["outputs"]["verify report"]["trace_markdown"]


def test_failed_deep_research_persists_partial_trace_without_network(tmp_path):
    engine, _, _ = _engine(tmp_path)
    state = engine.start("research_deep", {
        "question": "What should be checked?", "depth": "quick",
        "sources": ["web"], "model_free": True,
    })

    assert state.status == "failed"
    assert state.trace
    assert any(event["event"] == "search_failed" for event in state.trace)
    persisted = json.loads((tmp_path / "workflows" / f"{state.run_id}.json").read_text())
    assert persisted["trace"] == state.trace
