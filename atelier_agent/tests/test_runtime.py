import json

from atelier.runtime import (
    legacy_migration_plan,
    migrate_legacy_state,
    migrate_state,
    migration_plan,
    runtime_layout,
    rollback_migration,
)


def test_runtime_layout_initializes_and_validates(tmp_path):
    layout = runtime_layout(tmp_path / "home").initialize()
    result = layout.validate()
    assert result["valid"] is True
    assert json.loads(layout.manifest.read_text())["version"] == 1


def test_migration_plan_copy_and_rollback_preserve_source(tmp_path):
    source = tmp_path / "data"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "note.txt").write_text("keep", encoding="utf-8")
    destination = tmp_path / "home" / "library" / "legacy"
    plan = migration_plan(source, destination)
    assert plan["file_count"] == 1
    result = migrate_state(source, destination)
    assert (destination / "nested" / "note.txt").read_text() == "keep"
    assert (source / "nested" / "note.txt").exists()
    rollback = rollback_migration(result["record"])
    assert rollback["removed"] == [str(destination / "nested" / "note.txt")]
    assert (source / "nested" / "note.txt").exists()


def test_legacy_migration_maps_development_data_into_runtime_layout(tmp_path):
    source = tmp_path / "legacy-data"
    (source / "corpus" / "papers").mkdir(parents=True)
    (source / "corpus" / "papers" / "paper.pdf").write_bytes(b"pdf")
    (source / "vectorstore").mkdir()
    (source / "vectorstore" / "chroma.sqlite3").write_bytes(b"sqlite")
    (source / "workspaces.json").write_text("{\"workspaces\": []}\n", encoding="utf-8")

    layout = runtime_layout(tmp_path / "home")
    plan = legacy_migration_plan(source, layout)
    destinations = {item["destination"] for item in plan["files"]}
    assert str(layout.library / "corpus" / "papers" / "paper.pdf") in destinations
    assert str(layout.databases / "vectorstore" / "chroma.sqlite3") in destinations
    assert str(layout.workspaces / "registry.json") in destinations

    result = migrate_legacy_state(source, layout)
    assert result["copied"] == 3
    assert (layout.library / "corpus" / "papers" / "paper.pdf").read_bytes() == b"pdf"
    assert (layout.databases / "vectorstore" / "chroma.sqlite3").read_bytes() == b"sqlite"
    assert (layout.workspaces / "registry.json").exists()
    assert (source / "corpus" / "papers" / "paper.pdf").exists()
