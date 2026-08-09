from pathlib import Path

from atelier.package import export_runtime, package_check, restore_runtime
from atelier.performance import measure, service_baseline
from atelier.reliability import summarize_trials, wilson_interval
from eval.reliability_v2 import run_reliability_v2


def test_wilson_interval_and_failure_taxonomy():
    low, high = wilson_interval(8, 10)
    assert 0 < low < high < 1
    report = summarize_trials([
        {"success": True, "category": "code"},
        {"success": False, "category": "code", "failure_type": "tool_error"},
        {"success": False, "category": "paper", "failure_type": "citation_gap"},
    ], suite="smoke")
    assert report["trials"] == 3
    assert report["failure_taxonomy"] == {"citation_gap": 1, "tool_error": 1}
    assert report["by_category"]["code"]["trials"] == 2


def test_performance_measure_records_success_and_failure():
    assert measure("ok", lambda: 42).ok is True
    assert measure("bad", lambda: 1 / 0).ok is False


def test_package_check_passes_for_project():
    result = package_check(Path(__file__).parents[1])
    assert result["valid"] is True


def test_reliability_v2_runs_frozen_cross_component_cases():
    report = run_reliability_v2(repetitions=2)
    assert report["schema_version"] == 2
    assert report["trials"] == 14
    assert report["successes"] == 14
    assert set(report["frozen_cases"]) >= {"security.prompt_injection", "workflow.repo_inspect"}


def test_runtime_export_restore_is_path_safe(tmp_path):
    home = tmp_path / "home"
    (home / "library").mkdir(parents=True)
    (home / "library" / "note.txt").write_text("evidence", encoding="utf-8")
    archive = tmp_path / "runtime.zip"
    result = export_runtime(home, archive)
    assert result["files"] == 1
    restored = restore_runtime(archive, tmp_path / "restored")
    assert restored["restored"] == 1
    assert (tmp_path / "restored" / "library" / "note.txt").read_text() == "evidence"


def test_performance_baseline_includes_system_snapshot(tmp_path):
    class Service:
        def health(self): return {"status": "ok"}
        def workflows(self): return []
        def library(self): return {"count": 0}
        def route(self, _task): return {"status": "ok"}

    report = service_baseline(Service())
    assert report["all_ok"] is True
    assert report["system"]["free_disk_gib"] >= 0
