"""Runtime state: init, validation, migration, Finder actions, handoff, packaging."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from atelier.cli._app import (
    app,
    console,
    finder_app,
    handoff_app,
    package_app,
    state_app,
)
from atelier.config import settings


@app.command(hidden=True)
def init(
    home: Path | None = typer.Option(None, "--home", help="Runtime home (default ~/.atelier or ATELIER_HOME)."),
) -> None:
    """Initialize a versioned external Atelier runtime home."""
    from atelier.runtime import runtime_layout

    layout = runtime_layout(home).initialize()
    console.print(f"[green]Initialized Atelier runtime home:[/] {layout.root}")
    console.print_json(json.dumps(layout.to_dict()))


@state_app.command("validate")
def state_validate(home: Path | None = typer.Option(None, "--home")) -> None:
    """Validate runtime-home directories and manifest without changing state."""
    from atelier.runtime import runtime_layout

    result = runtime_layout(home).validate()
    console.print_json(json.dumps(result))
    if not result["valid"]:
        raise typer.Exit(code=1)


@state_app.command("plan")
def state_plan(
    source: Path = typer.Option(settings.legacy_data_dir, "--source", exists=True, file_okay=False),
    home: Path | None = typer.Option(None, "--home"),
) -> None:
    """Show a non-mutating plan for importing current repository state."""
    from atelier.runtime import legacy_migration_plan, runtime_layout

    console.print_json(json.dumps(legacy_migration_plan(source, runtime_layout(home))))


@state_app.command("migrate")
def state_migrate(
    source: Path = typer.Option(settings.legacy_data_dir, "--source", exists=True, file_okay=False),
    home: Path | None = typer.Option(None, "--home"),
) -> None:
    """Copy current state into a runtime home and write a rollback record."""
    from atelier.runtime import migrate_legacy_state, runtime_layout

    result = migrate_legacy_state(source, runtime_layout(home))
    console.print_json(json.dumps(result))


@state_app.command("rollback")
def state_rollback(record: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Remove only files listed in an explicit migration record; source stays intact."""
    from atelier.runtime import rollback_migration

    console.print_json(json.dumps(rollback_migration(record)))


@state_app.command("repair")
def state_repair(home: Path | None = typer.Option(None, "--home")) -> None:
    """Create missing runtime directories and revalidate the active home."""
    from atelier.runtime import runtime_layout

    layout = runtime_layout(home).initialize()
    result = layout.validate()
    console.print_json(json.dumps({"status": "repaired" if result["valid"] else "failed", **result}))
    if not result["valid"]:
        raise typer.Exit(code=1)


@finder_app.command("plan")
def finder_plan(
    action: str = typer.Argument(..., help="send_to_atelier, add_to_library, characterize_paper, or explain_file"),
    path: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Prepare one explicit Finder action without watching or indexing."""
    from atelier.finder import prepare_finder_action
    from atelier.workspace import WorkspaceError

    try:
        result = prepare_finder_action(action, path)
    except (ValueError, WorkspaceError, OSError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@finder_app.command("execute")
def finder_execute(
    action: str = typer.Argument(..., help="send_to_atelier, add_to_library, characterize_paper, or explain_file"),
    path: Path = typer.Argument(..., exists=True, readable=True),
    task: str | None = typer.Option(None, "--task", help="Optional task for send_to_atelier."),
) -> None:
    """Execute one explicit Finder action through the local Atelier service."""
    from atelier.finder import execute_finder_action
    from atelier.workspace import WorkspaceError

    try:
        result = execute_finder_action(action, path, task=task)
    except (ValueError, WorkspaceError, OSError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@handoff_app.command("create")
def handoff_create(
    target: str = typer.Option(..., "--target", help="claude, codex, or gemini"),
    task: str = typer.Option(..., "--task"),
    output: Path = typer.Option(..., "--output"),
    context: list[str] = typer.Option([], "--context"),
    evidence: list[str] = typer.Option([], "--evidence"),
    constraint: list[str] = typer.Option([], "--constraint"),
    requested_output: str = typer.Option("Return a concise, evidence-grounded result.", "--requested-output"),
    approve_external: bool = typer.Option(False, "--approve-external", help="Record explicit approval; this still does not send anything."),
    markdown: bool = typer.Option(False, "--markdown"),
) -> None:
    """Write a reviewable handoff file; no provider/API call is made."""
    from atelier.handoff import create_handoff, export_handoff

    try:
        bundle = create_handoff(target, task, selected_context=context, evidence=evidence,
                                constraints=constraint, requested_output=requested_output,
                                approved_for_external_transfer=approve_external)
        path = export_handoff(bundle, output, markdown=markdown)
    except (ValueError, OSError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(f"[green]Handoff bundle written:[/] {path}")

#: The package root to check by default. Derived from config rather than from
#: this file's location, so moving the module cannot silently retarget it.
PACKAGE_ROOT_OPT = typer.Option(settings.root, "--root", exists=True, file_okay=False)


@package_app.command("check")
def package_check_command(
    root: Path = PACKAGE_ROOT_OPT,
) -> None:
    """Check package files and Python syntax without building or mutating state."""
    from atelier.package import package_check

    result = package_check(root)
    console.print_json(json.dumps(result))
    if not result["valid"]:
        raise typer.Exit(code=1)


@package_app.command("export")
def package_export(
    output: Path = typer.Option(..., "--output"),
    home: Path | None = typer.Option(None, "--home"),
) -> None:
    """Export external runtime state to a portable ZIP backup."""
    from atelier.package import export_runtime
    from atelier.runtime import default_home

    try:
        result = export_runtime(home or default_home(), output)
    except (OSError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@package_app.command("restore")
def package_restore(
    archive: Path = typer.Option(..., "--archive", exists=True, readable=True),
    home: Path = typer.Option(..., "--home"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Restore an explicit runtime ZIP backup after path-safety validation."""
    from atelier.package import restore_runtime

    try:
        result = restore_runtime(archive, home, overwrite=overwrite)
    except (OSError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))
