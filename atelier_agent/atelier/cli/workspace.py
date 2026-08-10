"""Approved workspace roots and their capabilities."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from atelier.cli._app import (
    console,
    workspace_app,
)


@workspace_app.command("add")
def workspace_add(
    path: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    name: str | None = typer.Option(None, "--name", help="Stable workspace name."),
    capabilities: str = typer.Option(
        "read", "--capabilities", help="Comma-separated: read,write,execute,network."
    ),
    privacy: str = typer.Option("LOCAL_ONLY", "--privacy", help="LOCAL_ONLY or CLOUD_ALLOWED."),
) -> None:
    """Approve a directory as an Atelier workspace without opening it."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    requested = {item.strip() for item in capabilities.split(",") if item.strip()}
    try:
        workspace = get_workspace_manager().add(
            path, name=name, capabilities=requested, privacy=privacy.upper()
        )
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(
        f"[green]Approved[/] {workspace.name}: {workspace.root} "
        f"({', '.join(sorted(workspace.capabilities))}; {workspace.privacy})"
    )


@workspace_app.command("open")
def workspace_open(name: str = typer.Argument(...)) -> None:
    """Attach a workspace and make it the active relative-path root."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        workspace = get_workspace_manager().open(name)
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(f"[green]Open[/] {workspace.name}: {workspace.root}")


@workspace_app.command("close")
def workspace_close(name: str = typer.Argument(...)) -> None:
    """Detach a workspace; its approval remains in the registry."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        workspace = get_workspace_manager().close(name)
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(f"[yellow]Closed[/] {workspace.name}")


@workspace_app.command("list")
def workspace_list() -> None:
    """List approved workspaces, attachment state, capabilities, and privacy."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        manager = get_workspace_manager()
        active = manager.active().name
        workspaces = manager.list()
    except WorkspaceError as exc:
        active = ""
        workspaces = get_workspace_manager().list()
        console.print(f"[yellow]{exc}[/]")
    table = Table(title="Approved Atelier workspaces")
    table.add_column("Name", style="bold")
    table.add_column("Root")
    table.add_column("State")
    table.add_column("Capabilities")
    table.add_column("Privacy")
    for workspace in workspaces:
        if not workspace.root.exists() or not workspace.root.is_dir():
            state = "missing"
        else:
            state = "active" if workspace.name == active else ("open" if workspace.attached else "closed")
        table.add_row(
            workspace.name,
            str(workspace.root),
            state,
            ", ".join(sorted(workspace.capabilities)),
            workspace.privacy,
        )
    console.print(table)
