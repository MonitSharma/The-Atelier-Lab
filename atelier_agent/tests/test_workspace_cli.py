from pathlib import Path

from typer.testing import CliRunner

from atelier.cli import app
from atelier.workspace import WorkspaceManager


def test_cli_can_grant_capabilities_after_automatic_activation(
    tmp_path: Path, monkeypatch
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    registry = tmp_path / "registry.json"
    monkeypatch.setattr("atelier.workspace.settings.workspace_registry_path", registry)
    runner = CliRunner()

    listed = runner.invoke(app, ["--workspace", str(project), "workspace", "list"])
    assert listed.exit_code == 0, listed.output

    manager = WorkspaceManager(registry)
    workspace = manager.active()
    assert workspace.capabilities == {"read"}

    granted = runner.invoke(
        app,
        [
            "--workspace", str(project), "workspace", "grant", workspace.name,
            "--capabilities", "read,write,execute",
        ],
    )
    assert granted.exit_code == 0, granted.output
    assert WorkspaceManager(registry).get(workspace.name).capabilities == {
        "read", "write", "execute",
    }
