"""Configured models, local residency, and benchmarks."""

from __future__ import annotations

import json

import typer
from rich.table import Table

from atelier.cli._app import (
    console,
    models_app,
)


@models_app.command("list")
def models_list() -> None:
    """List configured roles, capabilities, install state, and memory estimates."""
    from models.lifecycle import ModelLifecycle

    table = Table(title="Atelier model lifecycle")
    for column in ("Role", "Model", "Configured", "Installed", "Resident", "Memory est.", "Context", "Modality"):
        table.add_column(column)
    for record in ModelLifecycle().list():
        table.add_row(
            record.role, record.model_id or "—", "yes" if record.configured else "no",
            "yes" if record.installed else "no", "yes" if record.resident else "no",
            f"{record.memory_estimate_gb:g} GB" if record.memory_estimate_gb else "—",
            f"{record.context_tokens:,}" if record.context_tokens else "—", record.modality,
        )
    console.print(table)


@models_app.command("status")
def models_status(as_json: bool = typer.Option(False, "--json")) -> None:
    """Show Ollama installation and residency status for configured roles."""
    from models.lifecycle import ModelLifecycle

    payload = ModelLifecycle().status()
    if as_json:
        console.print_json(json.dumps(payload, default=str))
        return
    console.print_json(json.dumps(payload, default=str))


@models_app.command("bench")
def models_bench(
    model: str = typer.Option(..., "--model", help="Ollama model ID to benchmark."),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
) -> None:
    """Run the frozen coding benchmark for one local model."""
    from models.lifecycle import ModelLifecycle

    with console.status(f"Benchmarking {model}..."):
        report = ModelLifecycle().bench(model, max_steps=max_steps)
    summary = report["by_model"][model]
    console.print(
        f"{model}: solve={summary['solve_rate']:.0%}, "
        f"latency={summary['mean_latency_s']:.1f}s, "
        f"tool_errors={summary['mean_tool_errors']:.1f}\n"
        f"Report: {report['report_path']}"
    )
