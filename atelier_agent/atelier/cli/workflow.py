"""Durable typed workflows, approvals, and destructive-operation confirmations."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.table import Table

from atelier.cli._app import (
    app,
    console,
    security_app,
    workflow_app,
)


@app.command("workflows", hidden=True)
def workflows_list(
    name: str | None = typer.Option(None, "--name", help="Describe one workflow."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """List the typed workflow catalog and its approval/recovery gates."""
    from atelier.workflows import get_workflow, list_workflows

    try:
        rows = [get_workflow(name)] if name else list_workflows()
    except KeyError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    payload = [row.to_dict() for row in rows]
    if as_json:
        console.print_json(json.dumps(payload))
        return
    table = Table(title="Atelier workflows")
    for column in ("name", "purpose", "capabilities", "approval", "recovery"):
        table.add_column(column)
    for row in rows:
        table.add_row(row.name, row.purpose, ", ".join(row.required_capabilities), row.approval_gate, row.recovery)
    console.print(table)


def _workflow_service():
    from atelier.service import AtelierService
    from atelier.workspace import get_workspace_manager

    manager = get_workspace_manager()
    return AtelierService(manager=manager), manager


@workflow_app.command("run")
def workflow_run(
    name: str = typer.Argument(..., help="Workflow name from `atelier workflows`."),
    input_json: str | None = typer.Option(None, "--input-json", help="Workflow input as a JSON object."),
    input_path: Path | None = typer.Option(None, "--input", exists=True, readable=True, help="JSON file containing workflow input."),
    approved: bool = typer.Option(False, "--approved", help="Pre-approve gates for this run."),
) -> None:
    """Start a durable workflow and run until completion or an approval gate."""
    if input_json and input_path:
        console.print("[red]Use only one of --input-json or --input.[/]")
        raise typer.Exit(code=2)
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8")) if input_path else json.loads(input_json or "{}")
        if not isinstance(payload, dict):
            raise ValueError("workflow input must be a JSON object")
        service, _ = _workflow_service()
        result = service.workflow_start(name, payload, approved=approved)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@workflow_app.command("status")
def workflow_status(run_id: str = typer.Argument(...)) -> None:
    """Show persisted workflow state, evidence, and checkpoints."""
    try:
        result = _workflow_service()[0].workflow_get(run_id)
    except (KeyError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@workflow_app.command("approve")
def workflow_approve(
    run_id: str = typer.Argument(...),
    decline: bool = typer.Option(False, "--decline", help="Decline the pending approval and cancel the run."),
) -> None:
    """Approve or decline a workflow gate and continue the run."""
    try:
        result = _workflow_service()[0].workflow_approve(run_id, approved=not decline)
    except (KeyError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@workflow_app.command("recover")
def workflow_recover(run_id: str = typer.Argument(...)) -> None:
    """Resume a failed or interrupted workflow from its last checkpoint."""
    try:
        result = _workflow_service()[0].workflow_recover(run_id)
    except (KeyError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))


@workflow_app.command("retention")
def workflow_retention(
    keep_successful: int = typer.Option(20, "--keep-successful", min=0, help="Protect this many recent completed/partial runs."),
    failed_days: int = typer.Option(30, "--failed-days", min=0, help="Only consider failed/cancelled runs older than this."),
    apply: bool = typer.Option(False, "--apply", help="Delete the exact dry-run candidates."),
) -> None:
    """Plan workflow-log cleanup; deletion requires explicit --apply."""
    from atelier.config import settings
    from atelier.workflow_retention import apply_retention, retention_candidates

    candidates = retention_candidates(
        settings.workflow_dir, keep_successful=keep_successful, failed_days=failed_days,
    )
    if apply:
        removed = apply_retention(candidates)
        console.print_json(json.dumps({"status": "applied", "removed": removed}))
    else:
        console.print_json(json.dumps({"status": "dry_run", "candidates": candidates}, default=str))


@security_app.command("request")
def security_request(operation: str = typer.Argument(..., help="Exact destructive command or operation to approve once.")) -> None:
    """Issue a one-use confirmation token; the token must match the exact operation."""
    service, _ = _workflow_service()
    console.print_json(json.dumps(service.issue_security_confirmation(operation), default=str))
