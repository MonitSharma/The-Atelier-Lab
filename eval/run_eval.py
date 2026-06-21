"""Run the eval suites and produce a reproducible reliability report.

    python -m eval.run_eval                 # both suites
    python -m eval.run_eval --mode docqa    # knowledge mode only
    python -m eval.run_eval --mode code     # build mode only
    python -m eval.run_eval --judge         # add the local LLM-as-judge

Also exposed as `atelier eval`. Reports are written to data/eval_reports/.
"""

from __future__ import annotations

import json
import shutil
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atelier.config import settings
from eval import metrics

ROOT = settings.root
DOCQA_FILE = ROOT / "eval" / "tasks_docqa" / "tasks.json"
CODE_DIR = ROOT / "eval" / "tasks_code"
COMBINED_DIR = ROOT / "eval" / "tasks_combined"
WORKSPACE = ROOT / ".eval_workspace"


# --------------------------------------------------------------------------- #
# Knowledge mode
# --------------------------------------------------------------------------- #
def ensure_corpus(corpus: list[str]) -> None:
    """Index the suite's corpus so doc-QA is self-contained and reproducible."""
    from rag.embed import get_embedder
    from rag.ingest import ingest_paths
    from rag.store import VectorStore

    paths = [str(ROOT / c) for c in corpus if (ROOT / c).exists()]
    chunks, _ = ingest_paths(paths)
    if chunks:
        store = VectorStore()
        store.add(chunks, get_embedder().embed_passages([c.text for c in chunks]))


def run_docqa(judge: bool = False, ingest: bool = True) -> dict[str, Any]:
    from rag.answer import answer_question
    from rag.retrieve import format_context

    spec = json.loads(DOCQA_FILE.read_text())
    if ingest:
        ensure_corpus(spec.get("corpus", []))

    rows: list[dict[str, Any]] = []
    for task in spec["tasks"]:
        t0 = time.time()
        ans = answer_question(task["question"])
        row: dict[str, Any] = {
            "id": task["id"],
            "category": task.get("category", "general"),
            "difficulty": task.get("difficulty", "easy"),
            "keyword": metrics.keyword_score(ans.text, task.get("expected_contains", [])),
            "retrieval_hit": int(metrics.retrieval_hit(
                ans.sources,
                task.get("expected_sources", task.get("expected_source")),
            )),
            "cited": int(metrics.cites_sources(ans.text)),
            "latency_s": round(time.time() - t0, 1),
            "answer": ans.text[:240],
        }
        row["correct"] = int(row["keyword"] >= 0.5)
        if judge:
            j = metrics.llm_judge(task["question"], ans.text, format_context(ans.hits))
            row["judge_correct"] = int(j["correct"])
            row["judge_grounded"] = int(j["grounded"])
        rows.append(row)

    agg_keys = ["correct", "keyword", "retrieval_hit", "cited"]
    if judge:
        agg_keys += ["judge_correct", "judge_grounded"]
    return {
        "rows": rows,
        "aggregate": metrics.aggregate(rows, agg_keys),
        "by_category": metrics.aggregate_by(rows, "category", agg_keys),
        "by_difficulty": metrics.aggregate_by(rows, "difficulty", agg_keys),
    }


# --------------------------------------------------------------------------- #
# Build mode
# --------------------------------------------------------------------------- #
def _default_agent_runner(prompt: str):
    from agent.react import ReActAgent
    from tools.registry import create_default_registry

    return ReActAgent(create_default_registry(), role="brain", max_steps=12, log=True).run(prompt)


def _tool_errors(trace: list[dict[str, Any]]) -> int:
    return sum(1 for e in trace if isinstance(e.get("observation"), dict)
               and e["observation"].get("status") == "error")


def _tools_used(trace: list[dict[str, Any]]) -> list[str]:
    tools: list[str] = []
    for entry in trace:
        decision = entry.get("decision")
        if isinstance(decision, dict) and isinstance(decision.get("tool"), str):
            tools.append(decision["tool"])
    return tools


def run_code_task(task_dir: Path, agent_runner: Callable[[str], Any] | None = None) -> dict[str, Any]:
    """Set up an isolated copy of a frozen task, run the agent, verify with pytest."""
    from tools.test_runner import run_tests

    spec = json.loads((task_dir / "task.json").read_text())
    work = WORKSPACE / spec["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for f in task_dir.iterdir():
        if f.is_file() and f.name != "task.json":
            shutil.copy2(f, work / f.name)

    rel = work.relative_to(ROOT).as_posix()
    prompt = spec["prompt"].format(path=rel)

    runner = agent_runner or _default_agent_runner
    t0 = time.time()
    result = runner(prompt)
    elapsed = round(time.time() - t0, 1)

    verify = run_tests({"path": rel})
    solved = bool(verify.get("passed_clean"))

    return {
        "id": spec["id"],
        "category": spec.get("category", "general"),
        "difficulty": spec.get("difficulty", "easy"),
        "edit_scope": spec.get("edit_scope", "single_file"),
        "solved": int(solved),
        "steps": getattr(result, "steps", None),
        "tool_errors": _tool_errors(getattr(result, "trace", []) or []),
        "agent_finished": int(getattr(result, "success", False)),
        "latency_s": elapsed,
        "test_summary": verify.get("summary", ""),
    }


def run_code(agent_runner: Callable[[str], Any] | None = None) -> dict[str, Any]:
    rows = [run_code_task(d, agent_runner) for d in sorted(CODE_DIR.iterdir())
            if d.is_dir() and (d / "task.json").exists()]
    agg_keys = ["solved", "tool_errors", "steps"]
    return {
        "rows": rows,
        "aggregate": metrics.aggregate(rows, agg_keys),
        "by_category": metrics.aggregate_by(rows, "category", agg_keys),
        "by_difficulty": metrics.aggregate_by(rows, "difficulty", agg_keys),
        "by_edit_scope": metrics.aggregate_by(rows, "edit_scope", agg_keys),
    }


# --------------------------------------------------------------------------- #
# Combined knowledge -> build mode
# --------------------------------------------------------------------------- #
def run_combined_task(
    task_dir: Path,
    agent_runner: Callable[[str], Any] | None = None,
    *,
    ingest: bool = True,
) -> dict[str, Any]:
    """Run a task that must use knowledge retrieval and then prove a code change."""
    from tools.test_runner import run_tests

    spec = json.loads((task_dir / "task.json").read_text())
    if ingest:
        ensure_corpus(spec.get("corpus", []))

    work = WORKSPACE / "combined" / spec["id"]
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    for f in task_dir.iterdir():
        if f.is_file() and f.name != "task.json":
            shutil.copy2(f, work / f.name)

    rel = work.relative_to(ROOT).as_posix()
    prompt = spec["prompt"].format(path=rel)

    runner = agent_runner or _default_agent_runner
    t0 = time.time()
    result = runner(prompt)
    elapsed = round(time.time() - t0, 1)

    trace = getattr(result, "trace", []) or []
    tools_used = _tools_used(trace)
    verify = run_tests({"path": rel})
    tests_passed = bool(verify.get("passed_clean"))
    used_search_notes = "search_notes" in tools_used
    solved = tests_passed and used_search_notes

    return {
        "id": spec["id"],
        "category": spec.get("category", "general"),
        "difficulty": spec.get("difficulty", "easy"),
        "edit_scope": spec.get("edit_scope", "single_file"),
        "solved": int(solved),
        "tests_passed": int(tests_passed),
        "used_search_notes": int(used_search_notes),
        "steps": getattr(result, "steps", None),
        "tool_errors": _tool_errors(trace),
        "tools_used": tools_used,
        "agent_finished": int(getattr(result, "success", False)),
        "latency_s": elapsed,
        "test_summary": verify.get("summary", ""),
    }


def run_combined(agent_runner: Callable[[str], Any] | None = None) -> dict[str, Any]:
    rows = [run_combined_task(d, agent_runner) for d in sorted(COMBINED_DIR.iterdir())
            if d.is_dir() and (d / "task.json").exists()]
    agg_keys = ["solved", "tests_passed", "used_search_notes", "tool_errors", "steps"]
    return {
        "rows": rows,
        "aggregate": metrics.aggregate(rows, agg_keys),
        "by_category": metrics.aggregate_by(rows, "category", agg_keys),
        "by_difficulty": metrics.aggregate_by(rows, "difficulty", agg_keys),
        "by_edit_scope": metrics.aggregate_by(rows, "edit_scope", agg_keys),
    }


# --------------------------------------------------------------------------- #
# Orchestration + report
# --------------------------------------------------------------------------- #
def run_all(mode: str = "all", judge: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "brain_model": settings.brain_model,
        "embed_model": settings.embed_model,
    }
    if mode in ("all", "docqa"):
        report["docqa"] = run_docqa(judge=judge)
    if mode in ("all", "code"):
        report["code"] = run_code()
    if mode in ("all", "combined"):
        report["combined"] = run_combined()
    return report


#: Metrics where higher is better (used by the regression gate).
HIGHER_BETTER = {"correct", "retrieval_hit", "cited", "solved",
                 "tests_passed", "used_search_notes", "judge_correct", "judge_grounded"}


def latest_report() -> dict[str, Any] | None:
    """The most recent saved report, or None if there are none yet."""
    out_dir = settings.data_dir / "eval_reports"
    if not out_dir.exists():
        return None
    reports = sorted(out_dir.glob("report_*.json"))
    if not reports:
        return None
    return json.loads(reports[-1].read_text())


def compare_reports(prev: dict[str, Any], cur: dict[str, Any], tol: float = 0.01) -> list[str]:
    """Return human-readable regressions where a 'higher is better' metric dropped."""
    regressions: list[str] = []
    for mode in ("docqa", "code", "combined"):
        if mode not in prev or mode not in cur:
            continue
        pa = prev[mode].get("aggregate", {})
        ca = cur[mode].get("aggregate", {})
        for key in ca:
            if key in HIGHER_BETTER and key in pa and ca[key] < pa[key] - tol:
                regressions.append(f"{mode}.{key}: {pa[key]:.3f} -> {ca[key]:.3f}")
    return regressions


def save_report(report: dict[str, Any]) -> Path:
    settings.ensure_dirs()
    out_dir = settings.data_dir / "eval_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"report_{ts}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    return path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["all", "docqa", "code", "combined"], default="all")
    parser.add_argument("--judge", action="store_true")
    args = parser.parse_args()

    rep = run_all(mode=args.mode, judge=args.judge)
    print(json.dumps(rep, indent=2, default=str))
    print("saved:", save_report(rep))
