"""Tests for the eval harness scaffolding (no live model).

Metrics are pure. The code-task runner is exercised with a fake agent so we can
assert the verify-with-pytest plumbing works without calling Ollama.
"""

import re
from types import SimpleNamespace

from eval import metrics
from eval.run_eval import CODE_DIR, run_code_task


def test_keyword_score() -> None:
    assert metrics.keyword_score("reasoning ceiling and error compounding",
                                 ["reasoning ceiling", "error compounding"]) == 1.0
    assert metrics.keyword_score("only one here: reasoning ceiling",
                                 ["reasoning ceiling", "error compounding"]) == 0.5
    assert metrics.keyword_score("nothing relevant", ["missing"]) == 0.0


def test_retrieval_and_citation_metrics() -> None:
    assert metrics.retrieval_hit(["Project.md", "README.md"], "Project.md")
    assert not metrics.retrieval_hit(["other.md"], "Project.md")
    assert metrics.cites_sources("see [1] and [2]")
    assert not metrics.cites_sources("no citations here")


def test_aggregate_means() -> None:
    rows = [{"solved": 1, "steps": 4}, {"solved": 0, "steps": 6}]
    agg = metrics.aggregate(rows, ["solved", "steps"])
    assert agg["solved"] == 0.5
    assert agg["steps"] == 5.0


def _fixing_runner(prompt: str):
    """Pretend-agent that actually fixes the bug, so verification should pass."""
    rel = re.search(r"`([^`]+)`", prompt).group(1)
    from eval.run_eval import ROOT

    path = ROOT / rel / "mathutils.py"
    path.write_text(path.read_text().replace("a - b", "a + b"))
    return SimpleNamespace(steps=3, success=True, trace=[{"observation": {"status": "success"}}])


def test_code_task_solved_when_agent_fixes() -> None:
    res = run_code_task(CODE_DIR / "add_bug", agent_runner=_fixing_runner)
    assert res["solved"] == 1
    assert res["tool_errors"] == 0
    assert res["agent_finished"] == 1


def test_code_task_unsolved_when_agent_does_nothing() -> None:
    res = run_code_task(
        CODE_DIR / "add_bug",
        agent_runner=lambda p: SimpleNamespace(steps=1, success=False, trace=[]),
    )
    assert res["solved"] == 0
