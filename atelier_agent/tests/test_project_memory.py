import json
from datetime import UTC, datetime, timedelta

from agent.project_memory import ProjectMemoryStore


def test_project_memory_isolated_and_exportable(tmp_path):
    store = ProjectMemoryStore(tmp_path / "memory.sqlite3")
    item = store.remember("alpha", "use Qwen for coding", kind="decision", source="benchmark.md")
    store.remember("beta", "unrelated note", kind="source_note")

    assert [row.id for row in store.list("alpha")] == [item.id]
    exported = store.export("alpha", tmp_path / "alpha.json")
    assert json.loads(exported.read_text()) [0]["project"] == "alpha"
    assert store.forget(item.id, "beta") is False
    assert store.forget(item.id, "alpha") is True


def test_project_memory_import_keeps_destination_namespace(tmp_path):
    source = ProjectMemoryStore(tmp_path / "source.sqlite3")
    source.remember("source-project", "keep this", kind="artifact")
    export_path = source.export("source-project", tmp_path / "export.json")
    destination = ProjectMemoryStore(tmp_path / "destination.sqlite3")
    assert destination.import_file("new-project", export_path) == 1
    assert destination.list("source-project") == []
    assert destination.list("new-project")[0].text == "keep this"


def test_project_memory_enforces_expiration_and_preserves_provenance(tmp_path):
    store = ProjectMemoryStore(tmp_path / "memory.sqlite3")
    expired = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    item = store.remember(
        "alpha", "temporary result", kind="task_state", source="run-1",
        expires_at=expired, provenance={"workflow": "data_analyze"}, task_id="run-1",
    )
    assert store.list("alpha") == []
    assert store.list("alpha", include_expired=True)[0].provenance == {"workflow": "data_analyze"}
    assert store.purge_expired("alpha") == 1
    assert store.list("alpha", include_expired=True) == []
    assert item.task_id == "run-1"


def test_project_entities_and_active_context_are_isolated(tmp_path):
    store = ProjectMemoryStore(tmp_path / "memory.sqlite3")
    store.set_active_context("alpha", "session-1")
    assert store.active_context("alpha") == {"project": "alpha", "session_id": "session-1"}
    store.upsert_entity("alpha", "task-1", "task", {"goal": "profile data"}, status="waiting")
    store.upsert_entity("beta", "task-2", "task", {"goal": "other"})
    assert store.get_entity("task-1")["status"] == "waiting"
    assert [row["entity_id"] for row in store.list_entities("alpha", entity_type="task")] == ["task-1"]
