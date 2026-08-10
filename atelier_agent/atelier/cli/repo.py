"""Deterministic repository inspection and verification commands."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.table import Table
from rich.text import Text

from atelier.cli._app import (
    console,
    repo_app,
)


def _approved_repo_path(path: Path, capability: str = "read") -> Path:
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        return get_workspace_manager().context().resolve(str(path), capability).path
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc


def _repository(path: Path, capability: str = "read"):
    from repo.inspector import RepositoryInspector

    return RepositoryInspector.for_path(_approved_repo_path(path, capability))


@repo_app.command("inspect")
def repo_inspect(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    as_json: bool = typer.Option(False, "--json", help="Print the complete JSON profile."),
) -> None:
    """Characterize a repository without model calls or source embedding."""
    inspector = _repository(path)
    profile = inspector.inspect()
    if as_json:
        console.print_json(json.dumps(profile, default=str))
        return
    git = profile["git"]["status"]
    table = Table(title=f"Repository: {profile['root']}")
    table.add_column("Dimension", style="bold")
    table.add_column("Finding")
    table.add_row("Git", "not a Git repository" if not git["is_git"] else f"{git['branch']} · {'clean' if git['clean'] else 'changes'}")
    table.add_row("Files", f"{profile['file_count']}" + (" (truncated)" if profile["truncated"] else ""))
    table.add_row("Languages", ", ".join(f"{name} {count}" for name, count in profile["languages"].items()) or "none")
    table.add_row("Packages", ", ".join(item["manager"] for item in profile["package_managers"]) or "none detected")
    table.add_row("Environments", ", ".join(item["language"] for item in profile["environments"]) or "none detected")
    table.add_row("Tests", ", ".join(item["framework"] for item in profile["test_frameworks"]) or "none detected")
    table.add_row("Entry points", str(len(profile["entry_points"])))
    table.add_row("Symbols", str(sum(len(item["symbols"]) for item in profile["symbols"])))
    table.add_row("Test links", str(len(profile["test_relationships"])))
    console.print(table)
    if profile["important_files"]:
        console.print("[bold]Important files:[/] " + ", ".join(item["file"] for item in profile["important_files"][:12]))


@repo_app.command("status")
def repo_status(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)) -> None:
    """Show Git branch, cleanliness, changed paths, and recent history."""
    inspector = _repository(path)
    payload = {"status": inspector.git_status(), "history": inspector.git_history(), "diff": inspector.git_diff()}
    console.print_json(json.dumps(payload, default=str))


@repo_app.command("symbols")
def repo_symbols(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)) -> None:
    """List deterministic symbols and imports without executing source code."""
    rows = _repository(path).symbols()
    for row in rows:
        console.print(f"[bold]{row['file']}[/] ({row['language']})")
        for symbol in row["symbols"]:
            console.print(f"  {symbol['kind']} {symbol['name']} : line {symbol['line']}")
        if row["imports"]:
            console.print("  imports: " + ", ".join(row["imports"]))


@repo_app.command("search")
def repo_search(
    pattern: str = typer.Argument(..., help="Regular expression to search."),
    path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
) -> None:
    """Search repository text deterministically and return file/line evidence."""
    from repo.inspector import RepositoryInspectionError

    try:
        hits = _repository(path).search(pattern)
    except RepositoryInspectionError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    table = Table(title=f"Repository search: {pattern}")
    table.add_column("File")
    table.add_column("Line")
    table.add_column("Text")
    for hit in hits:
        table.add_row(hit["file"], str(hit["line"]), hit["text"])
    console.print(table)


@repo_app.command("tests")
def repo_tests(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    run: bool = typer.Option(False, "--run", help="Run the detected primary test command."),
) -> None:
    """Detect test frameworks and optionally run the primary local test command."""
    inspector = _repository(path, "execute" if run else "read")
    frameworks = inspector.test_frameworks()
    if not frameworks:
        console.print("[yellow]No supported test framework detected.[/]")
        return
    table = Table(title="Detected repository tests")
    table.add_column("Framework")
    table.add_column("Command")
    table.add_column("Tests")
    for framework in frameworks:
        table.add_row(framework["framework"], framework.get("command", ""), str(len(framework.get("tests", []))))
    console.print(table)
    if not run:
        return
    command = frameworks[0].get("command")
    if not command:
        console.print("[yellow]No runnable command was detected.[/]")
        return
    if command.startswith("python -m pytest"):
        command_args = [sys.executable, "-m", "pytest", "-q"]
    else:
        command_args = command.split()
    result = subprocess.run(command_args, cwd=str(inspector.root), text=True, capture_output=True, check=False)
    console.print(Text((result.stdout + "\n" + result.stderr).strip()[-12000:]))
    if result.returncode:
        raise typer.Exit(code=result.returncode)
