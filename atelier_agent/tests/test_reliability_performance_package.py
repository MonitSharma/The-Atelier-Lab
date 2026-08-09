from pathlib import Path

from atelier.package import package_check
from atelier.performance import measure
from atelier.reliability import summarize_trials, wilson_interval


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
