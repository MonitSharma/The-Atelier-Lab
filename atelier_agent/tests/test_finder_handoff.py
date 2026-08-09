import json

from atelier.finder import prepare_finder_action
from atelier.handoff import create_handoff, export_handoff
from atelier.workspace import WorkspaceManager


def _manager(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(root, name="project", capabilities={"read", "write", "execute"})
    manager.open("project")
    manager.close("atelier")
    return manager


def test_finder_action_is_explicit_and_does_not_watch(tmp_path):
    result = prepare_finder_action("explain_file", "note.txt", _manager(tmp_path))
    assert result["status"] == "planned"
    assert result["watching"] is False
    assert result["requires_user_invocation"] is True


def test_handoff_export_is_local_and_unapproved_by_default(tmp_path):
    bundle = create_handoff("claude", "Review this result", evidence=["result.json"], constraints=["do not invent missing values"])
    target = export_handoff(bundle, tmp_path / "handoff.json")
    payload = json.loads(target.read_text())
    assert payload["approved_for_external_transfer"] is False
    assert payload["target"] == "claude"
