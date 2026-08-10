from pathlib import Path

import pytest

from atelier.workspace import WorkspaceError, WorkspaceManager, workspace_scope
from tools.files import run_read_file, run_write_file


def _manager(tmp_path: Path) -> WorkspaceManager:
    (tmp_path / "one").mkdir(exist_ok=True)
    (tmp_path / "two").mkdir(exist_ok=True)
    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.add(tmp_path / "one", name="one", capabilities={"read"})
    manager.add(tmp_path / "two", name="two", capabilities={"read", "write", "execute"})
    manager.open("one")
    manager.open("two")
    manager.close("atelier")
    return manager


def test_workspace_context_supports_multiple_attached_roots(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    (tmp_path / "one" / "note.txt").write_text("one", encoding="utf-8")
    manager = _manager(tmp_path)
    context = manager.context()

    assert context.active.name == "two"
    assert context.resolve(".").workspace.name == "two"
    assert context.resolve(str(tmp_path / "one" / "note.txt")).workspace.name == "one"


def test_relative_path_escape_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    manager = _manager(tmp_path)
    with pytest.raises(WorkspaceError, match="outside all approved"):
        manager.context().resolve("../../etc/passwd")


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "one" / "leak").symlink_to(outside)
    manager = _manager(tmp_path)

    with pytest.raises(WorkspaceError, match="outside all approved"):
        manager.context().resolve(str(tmp_path / "one" / "leak"))


def test_read_only_workspace_denies_writes(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    (tmp_path / "one" / "note.txt").write_text("safe", encoding="utf-8")
    manager = _manager(tmp_path)

    with workspace_scope(manager.context()):
        assert run_read_file({"path": "../one/note.txt"})["status"] == "success"
        result = run_write_file({"path": "../one/new.txt", "content": "nope"})

    assert result["status"] == "error"
    assert result["error_type"] == "path_not_allowed"
    assert not (tmp_path / "one" / "new.txt").exists()


def test_local_only_blocks_network_capability(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    manager = _manager(tmp_path)
    with pytest.raises(WorkspaceError, match="does not grant 'network'"):
        manager.context().require_network()


def test_network_capability_requires_cloud_policy(tmp_path: Path) -> None:
    (tmp_path / "one").mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    with pytest.raises(WorkspaceError, match="CLOUD_ALLOWED"):
        manager.add(
            tmp_path / "one",
            name="networked",
            capabilities={"read", "network"},
            privacy="LOCAL_ONLY",
        )


def test_activate_directory_scopes_cli_to_current_directory(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")

    workspace = manager.activate_directory(root)

    assert workspace.root == root.resolve()
    assert workspace.capabilities == {"read"}
    assert workspace.privacy == "LOCAL_ONLY"
    assert manager.context().resolve("README.md").workspace.name == workspace.name


def test_default_source_workspace_cannot_be_written_from_another_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "atelier-source"
    source.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    security_file = source / "security.py"
    security_file.write_text("policy", encoding="utf-8")
    monkeypatch.setattr("atelier.workspace.settings.root", source)

    manager = WorkspaceManager(tmp_path / "registry.json")
    manager.activate_directory(victim)

    assert manager.get("atelier").capabilities == {"read"}
    with pytest.raises(WorkspaceError, match="read-only"):
        manager.context().resolve(str(security_file), "write")

    with workspace_scope(manager.context()):
        result = run_write_file({"path": str(security_file), "content": "changed"})
    assert result["status"] == "error"
    assert result["error_type"] == "path_not_allowed"
    assert security_file.read_text(encoding="utf-8") == "policy"


def test_source_checkout_requires_explicit_upgrade_for_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "atelier-source"
    source.mkdir()
    security_file = source / "security.py"
    security_file.write_text("policy", encoding="utf-8")
    monkeypatch.setattr("atelier.workspace.settings.root", source)

    manager = WorkspaceManager(tmp_path / "registry.json")
    explicit = manager.add(
        source,
        name="atelier-dev",
        capabilities={"read", "write", "execute"},
    )
    manager.open(explicit.name)

    assert manager.context().resolve(str(security_file), "write").workspace.name == "atelier-dev"


def test_add_upgrades_an_auto_created_workspace(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    manager = WorkspaceManager(tmp_path / "registry.json")
    auto = manager.activate_directory(project)

    upgraded = manager.add(
        project,
        name="user-chosen-name",
        capabilities={"read", "write", "execute"},
    )

    assert upgraded.name == auto.name
    assert upgraded.capabilities == {"read", "write", "execute"}


def test_missing_workspace_approval_survives_reload(tmp_path: Path) -> None:
    removable = tmp_path / "removable"
    removable.mkdir()
    registry = tmp_path / "registry.json"
    manager = WorkspaceManager(registry)
    manager.add(removable, name="removable", capabilities={"read"})

    removable.rmdir()
    reloaded = WorkspaceManager(registry)

    assert reloaded.get("removable").root == removable.resolve()
    reloaded.close("removable")
    assert WorkspaceManager(registry).get("removable").attached is False
