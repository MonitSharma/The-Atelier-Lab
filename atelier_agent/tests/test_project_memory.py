import json

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
