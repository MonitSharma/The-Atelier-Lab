"""Reproducible benchmark for the dedicated coding-specialist role.

The benchmark deliberately uses small, frozen multi-file repositories. Each
candidate receives the same prompt and an isolated copy, then the result is
verified by pytest. Model output is never judged by its prose: a solved task is
one whose complete test suite passes.
"""

from __future__ import annotations

import json
import os
import resource
import shutil
import time
from pathlib import Path
from typing import Any

from atelier.config import settings

TASKS_DIR = settings.root / "eval" / "tasks_coding_specialist"
WORKSPACE = settings.root / ".coding_benchmark_workspace"
EDIT_TOOLS = {"write_file", "edit_file", "ast_edit"}


def _peak_memory_mib() -> float:
    """Return peak RSS for the benchmark process.

    Ollama serves models out of process, so this is an agent-process measure,
    not a complete unified-memory measurement. The report labels it clearly;
    Step 24 will add host-level residency sampling.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes; Linux reports KiB.
    bytes_used = usage if os.uname().sysname == "Darwin" else usage * 1024
    return round(bytes_used / (1024 * 1024), 2)


def _copy_task(task_dir: Path, task_id: str) -> Path:
    work = WORKSPACE / task_id
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)
    for source in task_dir.rglob("*"):
        if source.name == "task.json" or not source.is_file():
            continue
        destination = work / source.relative_to(task_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return work


def _local_path(path: str, task_id: str) -> str:
    """Normalize a tool path to the frozen task root for fair read metrics."""
    marker = f".coding_benchmark_workspace/{task_id}/"
    if marker in path:
        return path.split(marker, 1)[1]
    normalized = path.lstrip("./")
    prefix = f"{task_id}/"
    return normalized[len(prefix):] if normalized.startswith(prefix) else normalized


def _trace_metrics(
    trace: list[dict[str, Any]],
    events: list[dict[str, Any]],
    relevant: set[str],
    task_id: str,
) -> dict[str, Any]:
    tool_errors = 0
    invalid_edits = 0
    reads: list[str] = []
    changed_paths: set[str] = set()
    for entry in trace:
        observation = entry.get("observation")
        if isinstance(observation, dict) and observation.get("status") == "error":
            tool_errors += 1
        decision = entry.get("decision")
        if not isinstance(decision, dict):
            continue
        tool = decision.get("tool")
        arguments = decision.get("arguments")
        if not isinstance(arguments, dict):
            continue
        path = arguments.get("path")
        if isinstance(path, str) and tool == "read_file":
            reads.append(_local_path(path, task_id))
        if isinstance(path, str) and tool in EDIT_TOOLS:
            changed_paths.add(_local_path(path, task_id))
            if not isinstance(observation, dict) or observation.get("status") == "error":
                invalid_edits += 1
            if isinstance(observation, dict) and observation.get("syntax_ok") is False:
                invalid_edits += 1

    model_events = [event for event in events if event.get("kind") == "model_result"]
    prompt_tokens = sum(event.get("prompt_tokens") or 0 for event in model_events)
    completion_tokens = sum(event.get("completion_tokens") or 0 for event in model_events)
    unnecessary = sum(1 for path in reads if path not in relevant and path != ".")
    return {
        "reads": len(reads),
        "read_paths": reads,
        "unnecessary_reads": unnecessary,
        "invalid_edits": invalid_edits,
        "changed_paths": sorted(changed_paths),
        "tool_errors": tool_errors,
        "model_calls": len(model_events),
        "prompt_tokens": prompt_tokens or None,
        "completion_tokens": completion_tokens or None,
    }


def run_task(task_dir: Path, model: str, *, max_steps: int = 14) -> dict[str, Any]:
    from agent.react import ReActAgent
    from tools.registry import create_default_registry
    from tools.test_runner import run_tests

    spec = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    work = _copy_task(task_dir, spec["id"])
    rel = work.relative_to(settings.root).as_posix()
    prompt = spec["prompt"].format(path=rel)
    events: list[dict[str, Any]] = []
    started = time.perf_counter()
    runner_error = ""
    try:
        result = ReActAgent(
            create_default_registry(),
            role="coder",
            model=model,
            max_steps=max_steps,
            log=False,
            on_event=events.append,
        ).run(prompt)
    except Exception as exc:  # noqa: BLE001 - benchmark reports failures
        result = None
        runner_error = str(exc)
    latency = round(time.perf_counter() - started, 3)
    verify = run_tests({"path": str(work.resolve())})
    trace = getattr(result, "trace", []) or []
    metrics = _trace_metrics(trace, events, set(spec.get("relevant_files", [])), spec["id"])
    return {
        "id": spec["id"],
        "model": model,
        "category": spec.get("category", "multi_file"),
        "difficulty": spec.get("difficulty", "medium"),
        "edit_scope": spec.get("edit_scope", "multi_file"),
        "solved": int(bool(verify.get("passed_clean"))),
        "test_pass": int(bool(verify.get("passed_clean"))),
        "agent_finished": int(bool(getattr(result, "success", False))),
        "steps": getattr(result, "steps", None),
        "latency_s": latency,
        "peak_process_memory_mib": _peak_memory_mib(),
        "runner_error": runner_error,
        "test_summary": verify.get("summary", ""),
        **metrics,
    }


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [row[key] for row in rows if isinstance(row.get(key), (int, float))]
    return round(sum(values) / len(values), 3) if values else 0.0


def run(models: list[str], *, max_steps: int = 14) -> dict[str, Any]:
    """Run all frozen tasks for every candidate model name."""
    if not models:
        raise ValueError("Provide at least one model name.")
    rows = [run_task(task_dir, model, max_steps=max_steps)
            for model in models
            for task_dir in sorted(TASKS_DIR.iterdir())
            if task_dir.is_dir() and (task_dir / "task.json").exists()]
    by_model: dict[str, dict[str, Any]] = {}
    for model in models:
        selected = [row for row in rows if row["model"] == model]
        by_model[model] = {
            "tasks": len(selected),
            "solve_rate": round(sum(row["solved"] for row in selected) / (len(selected) or 1), 3),
            "test_pass_rate": round(sum(row["test_pass"] for row in selected) / (len(selected) or 1), 3),
            "mean_unnecessary_reads": _mean(selected, "unnecessary_reads"),
            "mean_invalid_edits": _mean(selected, "invalid_edits"),
            "mean_tool_errors": _mean(selected, "tool_errors"),
            "mean_latency_s": _mean(selected, "latency_s"),
            "mean_peak_process_memory_mib": _mean(selected, "peak_process_memory_mib"),
            "mean_prompt_tokens": _mean(selected, "prompt_tokens"),
            "mean_completion_tokens": _mean(selected, "completion_tokens"),
        }
    return {
        "schema_version": 1,
        "benchmark": "coding_specialist_v1",
        "tasks": len({row["id"] for row in rows}),
        "models": models,
        "by_model": by_model,
        "rows": rows,
    }


def save(report: dict[str, Any]) -> Path:
    output_dir = settings.data_dir / "coding_benchmark_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    path = output_dir / f"report_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path
