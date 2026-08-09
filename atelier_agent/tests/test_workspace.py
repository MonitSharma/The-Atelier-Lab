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
