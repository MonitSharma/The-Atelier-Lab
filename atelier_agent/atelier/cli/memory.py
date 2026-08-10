"""Long-term recall and project-scoped memory."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from atelier.cli._app import (
    app,
    console,
    project_app,
)


@app.command()
def remember(
    text: str = typer.Argument(..., help="The fact to store in long-term memory."),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags."),
) -> None:
    """Store a durable fact (persists across sessions)."""
    from agent.memory import get_memory

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    mid = get_memory().remember(text, tag_list)
    console.print(f"[green]Remembered[/] [dim]({mid})[/]: {text}")


@app.command()
def recall(
    query: str = typer.Argument(..., help="What to recall."),
    k: int = typer.Option(5, "-k", help="How many memories to return."),
) -> None:
    """Search long-term memory by meaning."""
    from agent.memory import get_memory

    memories = get_memory().recall(query, k=k)
    if not memories:
        console.print("[yellow]No memories yet. Add one with `atelier remember`.[/]")
        return
    table = Table(title=f"Recalled for: {query}")
    table.add_column("score")
    table.add_column("memory")
    table.add_column("tags", style="dim")
    for m in memories:
        table.add_row(f"{m.score}", m.text, ", ".join(m.tags))
    console.print(table)


@app.command("memory-migrate", hidden=True)
def memory_migrate() -> None:
    """Back up and re-embed semantic memory into a compatible collection."""
    from agent.memory import migrate_memory

    with console.status("Backing up and migrating semantic memory..."):
        result = migrate_memory()
    table = Table(show_header=False)
    table.add_row("Facts before", str(result["before"]))
    table.add_row("Facts after", str(result["after"]))
    table.add_row("Backup", result["backup"])
    console.print(Panel(table, title="Memory migration complete", border_style="green"))


@app.command()
def memory() -> None:
    """List everything in long-term memory."""
    from agent.memory import get_memory

    mems = get_memory().all()
    if not mems:
        console.print("[yellow]Memory is empty.[/]")
        return
    table = Table(title=f"Long-term memory ({len(mems)} facts)")
    table.add_column("id", style="dim")
    table.add_column("memory")
    table.add_column("tags", style="dim")
    for m in mems:
        table.add_row(m.id, m.text, ", ".join(m.tags))


@project_app.command("memory-add")
def project_memory_add(
    project: str = typer.Argument(..., help="Project namespace; memories never cross it automatically."),
    text: str = typer.Argument(..., help="The project fact, decision, or note."),
    kind: str = typer.Option("project", "--kind", help="project, decision, source_note, artifact, task_state, or durable_user_fact."),
    source: str | None = typer.Option(None, "--source", help="Evidence or file locator."),
    expires_at: str | None = typer.Option(None, "--expires-at", help="Optional ISO-8601 expiry."),
) -> None:
    """Remember an explicit project-scoped item."""
    from agent.project_memory import ProjectMemoryStore

    item = ProjectMemoryStore().remember(project, text, kind=kind, source=source, expires_at=expires_at)
    console.print(f"[green]Remembered[/] {item.id} in {project} ({item.kind})")


@project_app.command("memory-list")
def project_memory_list(
    project: str = typer.Argument(...),
    kind: str | None = typer.Option(None, "--kind"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List only the selected project's explicit memory."""
    from agent.project_memory import ProjectMemoryStore

    items = ProjectMemoryStore().list(project, kind=kind)
    if as_json:
        console.print_json(json.dumps([item.to_dict() for item in items]))
        return
    table = Table(title=f"Project memory: {project}")
    for column in ("id", "kind", "text", "source", "expires"):
        table.add_column(column)
    for item in items:
        table.add_row(item.id, item.kind, item.text, item.source or "", item.expires_at or "")
    console.print(table)


@project_app.command("memory-forget")
def project_memory_forget(
    project: str = typer.Argument(...), memory_id: str = typer.Argument(...),
) -> None:
    """Forget an item only when its project namespace also matches."""
    from agent.project_memory import ProjectMemoryStore

    if not ProjectMemoryStore().forget(memory_id, project):
        console.print("[yellow]No matching project memory was removed.[/]")
        raise typer.Exit(code=1)
    console.print(f"[green]Forgot[/] {memory_id}")


@project_app.command("memory-export")
def project_memory_export(project: str = typer.Argument(...), path: Path = typer.Argument(...)) -> None:
    """Export one project's memory to a portable JSON file."""
    from agent.project_memory import ProjectMemoryStore

    target = ProjectMemoryStore().export(project, path)
    console.print(f"[green]Exported[/] {target}")


@project_app.command("memory-import")
def project_memory_import(project: str = typer.Argument(...), path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Import project memory JSON into the selected namespace."""
    from agent.project_memory import ProjectMemoryStore

    count = ProjectMemoryStore().import_file(project, path)
    console.print(f"[green]Imported[/] {count} project memories into {project}")


@project_app.command("context")
def project_context(project: str = typer.Argument(...), as_json: bool = typer.Option(False, "--json")) -> None:
    """Show active session, task, artifact, and non-expired memory state for a project."""
    from agent.project_memory import ProjectMemoryStore

    store = ProjectMemoryStore()
    payload = {"project": project, "active": store.active_context(project),
               "memory": [item.to_dict() for item in store.list(project)],
               "sessions": store.list_entities(project, entity_type="session"),
               "tasks": store.list_entities(project, entity_type="task"),
               "artifacts": store.list_entities(project, entity_type="artifact")}
    if as_json:
        console.print_json(json.dumps(payload, default=str))
        return
    console.print_json(json.dumps(payload, default=str))


@project_app.command("session-start")
def project_session_start(
    project: str = typer.Argument(...),
    session_id: str | None = typer.Option(None, "--session-id"),
) -> None:
    """Create or activate an explicit project session."""
    import uuid

    from agent.project_memory import ProjectMemoryStore

    store = ProjectMemoryStore()
    session = session_id or f"session-{uuid.uuid4().hex[:12]}"
    result = store.upsert_entity(project, session, "session", {"project": project}, status="active")
    store.set_active_context(project, session)
    console.print_json(json.dumps(result, default=str))


@project_app.command("artifact-record")
def project_artifact_record(
    project: str = typer.Argument(...),
    artifact_id: str = typer.Argument(...),
    path: str = typer.Option(..., "--path"),
    kind: str = typer.Option("artifact", "--kind"),
) -> None:
    """Record an artifact locator and its project association without indexing it."""
    from agent.project_memory import ProjectMemoryStore

    result = ProjectMemoryStore().upsert_entity(project, artifact_id, "artifact", {"path": path, "kind": kind})
    console.print_json(json.dumps(result, default=str))
