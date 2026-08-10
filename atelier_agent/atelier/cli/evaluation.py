"""Evaluation, benchmarking, and reliability reporting."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from atelier.cli._app import (
    EVAL_PLOT_OUT_OPT,
    EVAL_PLOT_REPORT_OPT,
    app,
    console,
)
from atelier.config import settings


@app.command(hidden=True)
def eval(
    mode: str = typer.Option("all", "--mode", help="all | docqa | code | combined"),
    judge: bool = typer.Option(False, "--judge", help="Add the local LLM-as-judge (slower)."),
    gate: bool = typer.Option(False, "--gate", help="Fail (exit 1) if any metric regressed vs the last report."),
) -> None:
    """Run the reliability eval suites and print + save a report."""
    from eval.run_eval import compare_reports, latest_report, run_all, save_report

    prev = latest_report() if gate else None

    with console.status(f"Running eval ({mode})... this calls the local model, be patient."):
        report = run_all(mode=mode, judge=judge)
    path = save_report(report)

    if "docqa" in report:
        agg = report["docqa"]["aggregate"]
        t = Table(title="Knowledge mode (doc-QA)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("correct")
        t.add_column("retrieval")
        t.add_column("cited")
        for r in report["docqa"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""),
                f'{r["correct"]}', f'{r["retrieval_hit"]}', f'{r["cited"]}',
            )
        console.print(t)
        console.print(f"[bold]doc-QA[/] correct={agg['correct']:.0%}  "
                      f"retrieval_hit={agg['retrieval_hit']:.0%}  cited={agg['cited']:.0%}")

    if "code" in report:
        agg = report["code"]["aggregate"]
        t = Table(title="Build mode (code)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("scope")
        t.add_column("solved")
        t.add_column("steps")
        t.add_column("tool_errs")
        for r in report["code"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""), r.get("edit_scope", ""),
                f'{r["solved"]}', f'{r["steps"]}', f'{r["tool_errors"]}',
            )
        console.print(t)
        console.print(f"[bold]code[/] solved={agg['solved']:.0%}  "
                      f"avg_steps={agg['steps']:.1f}  avg_tool_errors={agg['tool_errors']:.1f}")

    if "combined" in report:
        agg = report["combined"]["aggregate"]
        t = Table(title="Combined mode (knowledge → build)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("solved")
        t.add_column("tests")
        t.add_column("search_notes")
        t.add_column("steps")
        for r in report["combined"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""),
                f'{r["solved"]}', f'{r["tests_passed"]}', f'{r["used_search_notes"]}',
                f'{r["steps"]}',
            )
        console.print(t)
        console.print(f"[bold]combined[/] solved={agg['solved']:.0%}  "
                      f"tests_passed={agg['tests_passed']:.0%}  "
                      f"used_search_notes={agg['used_search_notes']:.0%}  "
                      f"avg_steps={agg['steps']:.1f}")

    console.print(f"[dim]Report: {path}[/]")

    if gate:
        if prev is None:
            console.print("[yellow]Gate: no prior report to compare against — baseline saved.[/]")
        else:
            regressions = compare_reports(prev, report)
            if regressions:
                console.print(Panel(Text("\n".join(regressions)), title=Text("⚠ Regressions detected"),
                                    border_style="red"))
                raise typer.Exit(code=1)
            console.print("[green]Gate: no regressions vs. last report.[/]")


@app.command("benchmark-coding", hidden=True)
def benchmark_coding(
    models: list[str] | None = typer.Option(
        None, "--model", help="Candidate model ID; repeat for multiple candidates."
    ),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
) -> None:
    """Benchmark local coding candidates on frozen multi-file repositories."""
    from eval.coding_benchmark import run, save

    candidates = models or [
        name for name in (settings.coder_model, settings.brain_model, settings.worker_model)
        if name
    ]
    with console.status("Running coding benchmark; local models may take a while..."):
        report = run(candidates, max_steps=max_steps)
    path = save(report)
    table = Table(title="Coding specialist benchmark")
    table.add_column("Model")
    table.add_column("Solve")
    table.add_column("Unnecessary reads")
    table.add_column("Tool errors")
    table.add_column("Latency")
    for model, summary in report["by_model"].items():
        table.add_row(
            model,
            f"{summary['solve_rate']:.0%}",
            f"{summary['mean_unnecessary_reads']:.1f}",
            f"{summary['mean_tool_errors']:.1f}",
            f"{summary['mean_latency_s']:.1f}s",
        )
    console.print(table)
    console.print(f"Report: {path}")


@app.command("eval-plots", hidden=True)
def eval_plots(
    report: Path | None = EVAL_PLOT_REPORT_OPT,
    out: Path | None = EVAL_PLOT_OUT_OPT,
) -> None:
    """Generate SVG plots from a saved eval report."""
    from eval.plots import main

    try:
        paths = main(str(report) if report else None, str(out) if out else None)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    table = Table(title="Eval plots")
    table.add_column("File")
    for path in paths:
        table.add_row(str(path))
    console.print(table)


@app.command("benchmark-retrieval", hidden=True)
def benchmark_retrieval(
    k: int = typer.Option(6, "-k", help="Number of passages per query."),
) -> None:
    """Run the local scientific retrieval benchmark without reasoning-model calls."""
    from eval.retrieval import run_local_retrieval_benchmark

    try:
        report = run_local_retrieval_benchmark(k=k)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Retrieval benchmark failed:[/] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[bold]Retrieval hits:[/] {report['aggregate']['hits']}/{report['aggregate']['queries']}")
    console.print(f"[bold]Reference-dominated queries:[/] {report['aggregate']['reference_dominated_queries']}")
    console.print(f"[dim]Report: {report['output']}[/]")

@app.command("reliability", hidden=True)
def reliability_report(
    input_path: Path | None = typer.Option(None, "--input", exists=True, readable=True, help="JSON list of trial rows."),
    suite: str = typer.Option("manual", "--suite"),
    repetitions: int = typer.Option(3, "--repetitions", min=1, max=20),
) -> None:
    """Summarize trial outcomes with Wilson confidence intervals and failure taxonomy."""
    from atelier.reliability import summarize_trials

    try:
        if suite == "v2":
            from eval.reliability_v2 import run_reliability_v2

            console.print_json(json.dumps(run_reliability_v2(repetitions=repetitions), default=str))
            return
        rows = json.loads(input_path.read_text(encoding="utf-8")) if input_path else []
        if not isinstance(rows, list):
            raise ValueError("input must be a JSON list")
        console.print_json(json.dumps(summarize_trials(rows, suite=suite)))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc


@app.command("route-eval", hidden=True)
def route_eval_command() -> None:
    """Run the frozen human-labeled capability-routing evaluation."""
    from eval.capability_routing import run_capability_eval

    result = run_capability_eval()
    console.print_json(json.dumps(result, default=str))
    if result["successes"] != result["cases"]:
        raise typer.Exit(code=1)


@app.command("performance", hidden=True)
def performance_report() -> None:
    """Measure baseline latency for shared local service operations."""
    from atelier.performance import service_baseline
    from atelier.service import AtelierService

    console.print_json(json.dumps(service_baseline(AtelierService()), default=str))

@app.command("acceptance", hidden=True)
def acceptance_command(clean: bool = typer.Option(False, "--clean", help="Run the fresh-runtime end-to-end acceptance scenario.")) -> None:
    """Run deterministic offline acceptance checks without model or network calls."""
    from atelier.acceptance import run_acceptance, run_clean_acceptance

    result = (run_clean_acceptance if clean else run_acceptance)(Path(__file__).resolve().parent.parent)
    console.print_json(json.dumps(result, default=str))
    if result["status"] != "passed":
        raise typer.Exit(code=1)
