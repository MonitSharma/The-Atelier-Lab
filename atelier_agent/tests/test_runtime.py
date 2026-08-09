import json

from atelier.runtime import migrate_state, migration_plan, runtime_layout, rollback_migration


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
