"""Atelier command-line interface.

    atelier doctor                 check models, store, and embeddings
    atelier ingest PATH...         index documents, notes, images, and code
    atelier ask "question"         grounded answer over your knowledge base
    atelier sources                list what's currently indexed
    atelier chat                   interactive knowledge-mode session

Run `python -m atelier.cli ...` if you haven't `pip install -e .`'d the package.

The commands live in sibling modules grouped by concern (``knowledge``,
``agentic``, ``repo``, …). Importing them here is what registers them on the
Typer app, so the import list below is load-bearing, not decorative.
"""

# Command-module import order is part of the public help surface. Keep this
# deliberate order stable; Ruff's isort rule cannot express registration order.
# ruff: noqa: I001

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

# Importing each command module registers its commands on `app`. The modules are
# aliased with a leading underscore so they cannot collide with a command
# parameter of the same name (`--workspace`, for one).
from atelier.cli import knowledge as _knowledge  # noqa: F401
from atelier.cli import agentic as _agentic  # noqa: F401
from atelier.cli import evaluation as _evaluation  # noqa: F401
from atelier.cli import memory as _memory  # noqa: F401
from atelier.cli import models as _models  # noqa: F401
from atelier.cli import repo as _repo  # noqa: F401
from atelier.cli import research as _research  # noqa: F401
from atelier.cli import science as _science  # noqa: F401
from atelier.cli import state as _state  # noqa: F401
from atelier.cli import workflow as _workflow  # noqa: F401
from atelier.cli import workspace as _workspace  # noqa: F401
from atelier.cli._app import app, console
from atelier.cli._ui import _retrieved_context_panels, _sync_console_width
from atelier.config import settings

#: Re-exported for callers that predate the package split (``atelier.cli.app``
#: remains the console-script entry point).
__all__ = [
    "_retrieved_context_panels",
    "_sync_console_width",
    "app",
    "console",
    "main",
    "settings",
]


@app.callback()
def _root(
    ctx: typer.Context,
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "--root",
        exists=True,
        file_okay=False,
        readable=True,
        help="Use this directory as the active workspace. Defaults to the current directory.",
    ),
) -> None:
    """Enter Atelier in the current directory or an explicitly selected workspace."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    _sync_console_width()
    try:
        get_workspace_manager().activate_directory(workspace or Path.cwd())
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    if ctx.invoked_subcommand is None:
        from atelier.session import run_session

        run_session(console)


def _print_guide() -> None:
    console.print(Panel(
        "[bold cyan]The daily Atelier loop[/]\n\n"
        "[bold]1. ingest[/] a paper, document, image, archive, study folder, or code folder\n"
        "[bold]2. ask[/] research, study, or document questions grounded in your indexed material\n"
        "[bold]3. deep-research[/] investigate an external question with bounded counter-search\n"
        "[bold]4. agent[/] ask Atelier to inspect or change an approved repository\n"
        "[bold]5. code-fix[/] run the certified inspect → edit → test workflow\n\n"
        "Everything is local by default. Use [bold]doctor[/] when something is unclear.",
        title="Atelier quick guide", border_style="cyan",
    ))
    table = Table(title="Core commands", show_header=True, header_style="bold")
    table.add_column("Command", style="bold cyan")
    table.add_column("Use it for")
    table.add_row("ingest PATH", "Index a file or folder for retrieval")
    table.add_row("sources", "See what is currently indexed")
    table.add_row("search QUERY", "Inspect matching passages without model synthesis")
    table.add_row("ask QUESTION", "Get a grounded answer with citations")
    table.add_row("paper PDF", "Create a cached scientific-paper characterization")
    table.add_row("deep-research QUESTION", "Run iterative web + scholarly discovery and cited synthesis")
    table.add_row("agent TASK", "Combine research lookup with repository work")
    table.add_row("code-fix TASK", "Make and test a controlled code change")
    table.add_row("remember / recall", "Store or retrieve durable project facts")
    table.add_row("doctor", "Check models, index, memory, and workspaces")
    console.print(table)
    console.print(
        "[dim]Examples: atelier ingest ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx  ·  "
        "atelier ask \"What are the plan's falsifiers?\"[/]"
    )
    console.print("[dim]Less common integrations and diagnostics: atelier advanced-help[/]")


@app.command("guide", rich_help_panel="Help")
def guide() -> None:
    """Show the short daily-use guide."""
    _print_guide()


@app.command("help", hidden=True)
def help_command() -> None:
    """Alias for `atelier guide`, useful inside the interactive session."""
    _print_guide()


@app.command("advanced-help", rich_help_panel="Help")
def advanced_help() -> None:
    """List advanced commands that are intentionally hidden from the daily help."""
    console.print(Panel(
        "These commands remain available for specific workflows; they are not required for normal research use.",
        title="Advanced Atelier commands", border_style="magenta",
    ))
    table = Table(show_header=True, header_style="bold")
    table.add_column("Area", style="bold")
    table.add_column("Commands")
    table.add_row("Visual / research", "paper-visual, profile, research-lookup")
    table.add_row("Model / retrieval evaluation", "eval, benchmark-coding, benchmark-retrieval, eval-plots")
    table.add_row("Local services", "serve, mcp, tools")
    table.add_row("Projects / science", "project, quantum, optimize")
    table.add_row("Runtime / workflows", "init, state, workflow, security, acceptance")
    table.add_row("Diagnostics", "route, route-eval, reliability, performance, models bench")
    table.add_row("External integrations", "finder, handoff, package, research")
    console.print(table)
    console.print("[dim]Full reference: docs/ATELIER_USER_GUIDE.md[/]")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
