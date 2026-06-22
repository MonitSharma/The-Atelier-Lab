"""Tests for the eval harness scaffolding (no live model).

Metrics are pure. The code-task runner is exercised with a fake agent so we can
assert the verify-with-pytest plumbing works without calling Ollama.
"""

import re
from types import SimpleNamespace

from eval import metrics
from eval.run_eval import CODE_DIR, COMBINED_DIR, run_code, run_code_task, run_combined_task


def test_keyword_score() -> None:
    assert metrics.keyword_score("reasoning ceiling and error compounding",
                                 ["reasoning ceiling", "error compounding"]) == 1.0
    assert metrics.keyword_score("only one here: reasoning ceiling",
                                 ["reasoning ceiling", "error compounding"]) == 0.5
    assert metrics.keyword_score("nothing relevant", ["missing"]) == 0.0


def test_retrieval_and_citation_metrics() -> None:
    assert metrics.retrieval_hit(["Project.md", "README.md"], "Project.md")
    assert metrics.retrieval_hit(["README.md"], ["Project.md", "README.md"])
    assert not metrics.retrieval_hit(["other.md"], "Project.md")
    assert metrics.cites_sources("see [1] and [2]")
    assert not metrics.cites_sources("no citations here")


def test_aggregate_means() -> None:
    rows = [{"solved": 1, "steps": 4}, {"solved": 0, "steps": 6}]
    agg = metrics.aggregate(rows, ["solved", "steps"])
    assert agg["solved"] == 0.5
    assert agg["steps"] == 5.0


def test_aggregate_by_metadata() -> None:
    rows = [
        {"difficulty": "easy", "solved": 1},
        {"difficulty": "easy", "solved": 0},
        {"difficulty": "medium", "solved": 1},
    ]
    grouped = metrics.aggregate_by(rows, "difficulty", ["solved"])
    assert grouped["easy"]["solved"] == 0.5
    assert grouped["medium"]["solved"] == 1.0


def _fixing_runner(prompt: str):
    """Pretend-agent that actually fixes the bug, so verification should pass."""
    rel = re.search(r"`([^`]+)`", prompt).group(1)
    from eval.run_eval import ROOT

    path = ROOT / rel / "mathutils.py"
    path.write_text(path.read_text().replace("a - b", "a + b"))
    return SimpleNamespace(steps=3, success=True, trace=[{"observation": {"status": "success"}}])


def _combined_fixing_runner(prompt: str):
    rel = re.search(r"`([^`]+)`", prompt).group(1)
    from eval.run_eval import ROOT

    root = ROOT / rel
    replacements = {
        "package_meta.py": ('LICENSE = "MIT"', 'LICENSE = "Apache-2.0"'),
        "project_prefs.py": ('TEST_FRAMEWORK = "unittest"', 'TEST_FRAMEWORK = "pytest"'),
        "runtime_policy.py": ("CLOUD_APIS_ALLOWED = True", "CLOUD_APIS_ALLOWED = False"),
    }
    for filename, (old, new) in replacements.items():
        path = root / filename
        if path.exists():
            path.write_text(path.read_text().replace(old, new))
    return SimpleNamespace(
        steps=5,
        success=True,
        trace=[
            {"decision": {"tool": "search_notes"}, "observation": {"status": "success"}},
            {"decision": {"tool": "edit_file"}, "observation": {"status": "success"}},
            {"decision": {"tool": "test_runner"}, "observation": {"status": "success"}},
        ],
    )


def test_code_task_solved_when_agent_fixes() -> None:
    res = run_code_task(CODE_DIR / "add_bug", agent_runner=_fixing_runner)
    assert res["solved"] == 1
    assert res["category"] == "arithmetic"
    assert res["difficulty"] == "easy"
    assert res["edit_scope"] == "single_line"
    assert res["tool_errors"] == 0
    assert res["agent_finished"] == 1


def test_combined_task_requires_tests_and_search_notes() -> None:
    res = run_combined_task(
        COMBINED_DIR / "license_preference",
        agent_runner=_combined_fixing_runner,
        ingest=False,
    )
    assert res["solved"] == 1
    assert res["tests_passed"] == 1
    assert res["used_search_notes"] == 1


def test_combined_task_unsolved_without_search_notes() -> None:
    def runner_without_search(prompt: str):
        result = _combined_fixing_runner(prompt)
        result.trace = [e for e in result.trace if e["decision"]["tool"] != "search_notes"]
        return result

    res = run_combined_task(
        COMBINED_DIR / "license_preference",
        agent_runner=runner_without_search,
        ingest=False,
    )
    assert res["tests_passed"] == 1
    assert res["used_search_notes"] == 0
    assert res["solved"] == 0


def test_regression_gate_flags_drops() -> None:
    from eval.run_eval import compare_reports

    prev = {"docqa": {"aggregate": {"correct": 1.0, "retrieval_hit": 1.0}},
            "code": {"aggregate": {"solved": 1.0}}}
    cur = {"docqa": {"aggregate": {"correct": 0.8, "retrieval_hit": 1.0}},
           "code": {"aggregate": {"solved": 1.0}}}
    regressions = compare_reports(prev, cur)
    assert len(regressions) == 1
    assert "docqa.correct" in regressions[0]


def test_regression_gate_passes_when_stable() -> None:
    from eval.run_eval import compare_reports

    rep = {"code": {"aggregate": {"solved": 1.0}}}
    assert compare_reports(rep, rep) == []


def test_code_task_unsolved_when_agent_does_nothing() -> None:
    res = run_code_task(
        CODE_DIR / "add_bug",
        agent_runner=lambda p: SimpleNamespace(steps=1, success=False, trace=[]),
    )
    assert res["solved"] == 0


def test_code_task_records_agent_crash() -> None:
    def crashing_runner(prompt: str):
        raise RuntimeError("model disconnected")

    res = run_code_task(CODE_DIR / "add_bug", agent_runner=crashing_runner)
    assert res["solved"] == 0
    assert res["agent_finished"] == 0
    assert "model disconnected" in res["runner_error"]


def test_code_report_includes_metadata_breakdowns() -> None:
    res = run_code(agent_runner=lambda p: SimpleNamespace(steps=1, success=False, trace=[]))
    assert len(res["rows"]) >= 10
    assert "easy" in res["by_difficulty"]
    assert "medium" in res["by_difficulty"]
    assert "single_line" in res["by_edit_scope"]
    assert "multi_line" in res["by_edit_scope"]


def test_combined_task_records_agent_crash() -> None:
    def crashing_runner(prompt: str):
        raise RuntimeError("model disconnected")

    res = run_combined_task(
        COMBINED_DIR / "license_preference",
        agent_runner=crashing_runner,
        ingest=False,
    )
    assert res["solved"] == 0
    assert res["tests_passed"] == 0
    assert res["used_search_notes"] == 0
    assert "model disconnected" in res["runner_error"]
