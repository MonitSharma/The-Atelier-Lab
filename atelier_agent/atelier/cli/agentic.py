"""Build mode: the agent loop, code fixes, routing, and tool servers."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from atelier.cli._app import (
    app,
    console,
)


@app.command()
def agent(
    goal: str = typer.Argument(..., help="The task for the agent to accomplish."),
    heavy: bool = typer.Option(False, "--heavy", help="Use the heavy reasoning model."),
    shell: bool = typer.Option(False, "--shell", help="Allow the (powerful) shell tool."),
    memory: bool = typer.Option(False, "--memory", help="Recall relevant long-term memories first."),
    max_steps: int = typer.Option(10, "--max-steps", help="Max reasoning/tool steps."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Stream each step."),
) -> None:
    """Run the full dual-mode agent (knowledge + build) on a task."""
    from agent.react import ReActAgent
    from atelier.workspace import get_workspace_manager
    from tools.registry import create_default_registry

    role = "heavy" if heavy else "brain"

    def on_event(ev: dict) -> None:
        kind = ev.get("kind")
        if kind == "tool_call":
            console.print(f"[cyan]→ step {ev['step']}[/] [bold]{ev['tool']}[/] "
                          f"[dim]{ev.get('thought', '')}[/]")
        elif kind == "observation":
            color = "green" if ev.get("status") == "success" else "red"
            console.print(f"  [{color}]observed: {ev.get('status')}[/] from {ev.get('tool')}")
        elif kind == "parse_error":
            console.print(f"  [yellow]reflect: bad output — {ev.get('detail')}[/]")

    registry = create_default_registry(
        include_shell=shell,
        workspace=get_workspace_manager().context(),
    )
    runner = ReActAgent(registry, role=role, max_steps=max_steps,
                        verbose=False, on_event=on_event if verbose else None,
                        use_memory=memory)
    with console.status("Atelier is working..."):
        result = runner.run(goal)

    if result.success:
        console.print(Panel(Text(result.answer or ""), title=f"Done in {result.steps} steps",
                            border_style="green"))
    else:
        console.print(Panel(f"Did not finish within {result.steps} steps.",
                            title="Incomplete", border_style="red"))
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")


@app.command("code-fix")
def code_fix(
    goal: str = typer.Argument(..., help="Coding task to complete."),
    path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
    escalation: bool = typer.Option(True, "--escalate/--no-escalate", help="Retry with the brain role if the coder fails."),
    rollback: bool = typer.Option(False, "--rollback-on-failure", help="Restore workflow edits if the final certificate fails."),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
    as_json: bool = typer.Option(False, "--json", help="Print the complete certificate JSON."),
) -> None:
    """Run the typed inspect → edit → test → certificate coding workflow."""
    from agent.coding_workflow import BuildWorkflow
    from atelier.workspace import WorkspaceError, get_workspace_manager

    manager = get_workspace_manager()
    try:
        context = manager.context()
        repository = context.resolve(str(path), "execute").path
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc

    with console.status("Running certified coding workflow..."):
        result = BuildWorkflow(repository, workspace=context).run(
            goal,
            role="coder",
            escalation_role="brain" if escalation else None,
            max_steps=max_steps,
            rollback_on_failure=rollback,
        )
    certificate = result.certificate.to_dict()
    if as_json:
        console.print_json(json.dumps(certificate, default=str))
    else:
        table = Table(title="Build Agent v2 certificate")
        table.add_column("Stage")
        table.add_column("Status")
        table.add_column("Evidence")
        for stage in result.certificate.stages:
            color = {"passed": "green", "failed": "red", "skipped": "yellow"}[stage.status]
            table.add_row(stage.name, f"[{color}]{stage.status}[/]", stage.detail[:180])
        console.print(table)
        console.print(
            f"Certificate: [{'green' if result.accepted else 'red'}]"
            f"{'accepted' if result.accepted else 'rejected'}[/] · "
            f"attempts={result.certificate.attempts} · "
            f"changed={len(result.certificate.changed_files)}"
        )
    if not result.accepted:
        raise typer.Exit(code=1)

@app.command(hidden=True)
def route(
    task: str = typer.Argument(..., help="A task to classify and route."),
    backend: str = typer.Option("auto", "--backend", help="auto | finetuned | heuristic"),
) -> None:
    """Classify a task by capability and show the local route decision."""
    from agent.capability_router import CapabilityRouter

    r = CapabilityRouter(backend=backend)
    with console.status("Routing..."):
        decision = r.decide(task)
    color = "red" if decision.abstain else ("green" if decision.difficulty == "easy" else "yellow")
    console.print(Panel(
        Text(
            f"domain: {decision.domain}\nworkflow: {decision.workflow}\n"
            f"difficulty: {decision.difficulty}\nrole: {decision.role}\n"
            f"model: {decision.model or 'abstain'}\nmodality: {decision.modality}\n"
            f"privacy: {decision.privacy}\nnetwork: {decision.requires_network}\n"
            f"memory: {decision.use_memory}\nreason: {decision.reason}"
        ),
        title=Text("Router decision"), border_style=color))

@app.command(hidden=True)
def mcp(shell: bool = typer.Option(False, "--shell", help="Expose the shell tool too.")) -> None:
    """Run the MCP tool bridge for an external MCP client; not for interactive use."""
    from atelier.mcp_server import main as mcp_main

    mcp_main(include_shell=shell)


@app.command(name="tools", hidden=True)
def list_tools(shell: bool = typer.Option(False, "--shell")) -> None:
    """List the tools the agent can use."""
    from tools.registry import create_default_registry

    registry = create_default_registry(include_shell=shell)
    table = Table(title="Agent tools")
    table.add_column("Tool", style="bold")
    table.add_column("Description")
    for tool in registry.list_tools():
        table.add_row(tool.name, tool.description)
    console.print(table)


@app.command(hidden=True)
def serve(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind only to localhost by default."),
    port: int = typer.Option(8787, "--port", min=1, max=65535),
) -> None:
    """Run the optional API; loopback is the safe default for the web UI."""
    from atelier.api import run_server

    console.print(f"Atelier API listening on http://{host}:{port}")
    run_server(host=host, port=port)
