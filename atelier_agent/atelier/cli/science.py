"""Deterministic quantum-circuit and optimization commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from atelier.cli._app import (
    console,
    optimize_app,
    quantum_app,
)


@quantum_app.command("inspect")
def quantum_inspect(
    qasm: str | None = typer.Option(None, "--qasm", help="Inline OpenQASM 2 source."),
    path: Path | None = typer.Option(None, "--path", exists=True, readable=True),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect a circuit without executing arbitrary code or contacting a backend."""
    from tools.science import run_quantum_inspect

    if qasm is None and path is None:
        console.print("[red]Provide --qasm or --path.[/]")
        raise typer.Exit(code=2)
    if qasm is None:
        from atelier.workspace import WorkspaceError, get_workspace_manager

        try:
            approved = get_workspace_manager().context().resolve(str(path), "read").path
            qasm = approved.read_text(encoding="utf-8")
        except (WorkspaceError, OSError) as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=2) from exc
    result = run_quantum_inspect({"qasm": qasm})
    if as_json:
        console.print_json(json.dumps(result, default=str))
        return
    console.print_json(json.dumps(result, default=str))


@quantum_app.command("simulate")
def quantum_simulate(
    qasm: str | None = typer.Option(None, "--qasm", help="Inline OpenQASM 2 source."),
    path: Path | None = typer.Option(None, "--path", exists=True, readable=True),
    shots: int = typer.Option(1024, "--shots", min=1, max=1_000_000),
) -> None:
    """Simulate a small common-gate circuit with the local NumPy statevector fallback."""
    from tools.science import simulate_qasm_text

    if qasm is None and path is None:
        console.print("[red]Provide --qasm or --path.[/]")
        raise typer.Exit(code=2)
    if qasm is not None:
        text = qasm
    else:
        from atelier.workspace import WorkspaceError, get_workspace_manager

        try:
            approved = get_workspace_manager().context().resolve(str(path), "read").path
            text = approved.read_text(encoding="utf-8")
        except (WorkspaceError, OSError) as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=2) from exc
    result = simulate_qasm_text(text, shots=shots)
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


@quantum_app.command("transpile")
def quantum_transpile(
    qasm: str | None = typer.Option(None, "--qasm", help="Inline OpenQASM 2 source."),
    path: Path | None = typer.Option(None, "--path", exists=True, readable=True),
    optimization_level: int = typer.Option(1, "--optimization-level", min=0, max=3),
) -> None:
    """Transpile with optional Qiskit and report an explicit fallback when absent."""
    from tools.science import transpile_qasm_text

    if qasm is None and path is None:
        console.print("[red]Provide --qasm or --path.[/]")
        raise typer.Exit(code=2)
    if qasm is not None:
        text = qasm
    else:
        from atelier.workspace import WorkspaceError, get_workspace_manager

        try:
            approved = get_workspace_manager().context().resolve(str(path), "read").path
            text = approved.read_text(encoding="utf-8")
        except (WorkspaceError, OSError) as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=2) from exc
    result = transpile_qasm_text(text, optimization_level=optimization_level)
    console.print_json(json.dumps(result, default=str))
    if result.get("status") == "error":
        raise typer.Exit(code=2)


@quantum_app.command("compare-backends")
def quantum_compare_backends(
    profile: Path = typer.Argument(..., exists=True, readable=True, help="JSON list of backend capacity profiles."),
    qasm: str | None = typer.Option(None, "--qasm", help="Inline OpenQASM 2 source."),
    path: Path | None = typer.Option(None, "--path", exists=True, readable=True),
) -> None:
    """Compare circuit resource needs against explicit provider-free profiles."""
    from tools.science import compare_quantum_backends

    try:
        from atelier.workspace import WorkspaceError, get_workspace_manager

        approved_profile = get_workspace_manager().context().resolve(str(profile), "read").path
        payload = json.loads(approved_profile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, WorkspaceError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    backends = payload.get("backends") if isinstance(payload, dict) else payload
    if qasm is None and path is None:
        console.print("[red]Provide --qasm or --path.[/]")
        raise typer.Exit(code=2)
    if qasm is not None:
        text = qasm
    else:
        from atelier.workspace import WorkspaceError, get_workspace_manager

        try:
            approved = get_workspace_manager().context().resolve(str(path), "read").path
            text = approved.read_text(encoding="utf-8")
        except (WorkspaceError, OSError) as exc:
            console.print(f"[red]{exc}[/]")
            raise typer.Exit(code=2) from exc
    result = compare_quantum_backends(text, backends)
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


@optimize_app.command("validate")
def optimize_validate(
    path: Path = typer.Argument(..., exists=True, readable=True, help="JSON optimization problem and candidate solution."),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Validate an LP/QUBO-style candidate from a JSON file."""
    from tools.science import run_optimization_validate

    try:
        problem = json.loads(path.read_text(encoding="utf-8"))
        result = run_optimization_validate({"problem": problem})
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print_json(json.dumps(result, default=str))
    if result.get("status") == "success" and not result.get("feasible"):
        raise typer.Exit(code=1)


def _optimization_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc


@optimize_app.command("solve")
def optimize_solve(path: Path = typer.Argument(..., exists=True, readable=True)) -> None:
    """Solve a small LP or binary QUBO locally and print the candidate solution."""
    from tools.science import solve_optimization

    result = solve_optimization(_optimization_json(path))
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


@optimize_app.command("compare")
def optimize_compare(
    path: Path = typer.Argument(..., exists=True, readable=True),
    solutions: Path = typer.Option(..., "--solutions", exists=True, readable=True),
) -> None:
    """Rank explicit candidate solutions against a problem's constraints and objective."""
    from tools.science import compare_optimization_solutions

    problem = _optimization_json(path)
    candidates = _optimization_json(solutions)
    result = compare_optimization_solutions(problem, candidates if isinstance(candidates, list) else candidates.get("solutions", []))
    console.print_json(json.dumps(result, default=str))
