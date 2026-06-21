import json

from eval.plots import generate_plots, load_report


def _sample_report():
    return {
        "docqa": {
            "aggregate": {"correct": 1.0, "retrieval_hit": 0.9, "cited": 0.8},
            "by_category": {
                "architecture": {"correct": 1.0},
                "rag": {"correct": 0.5},
            },
        },
        "code": {
            "aggregate": {"solved": 0.6, "tool_errors": 0.2, "steps": 5.0},
            "by_difficulty": {
                "easy": {"solved": 1.0},
                "medium": {"solved": 0.25},
            },
            "by_edit_scope": {
                "single_line": {"solved": 1.0},
                "multi_line": {"solved": 0.0},
            },
            "rows": [
                {"id": "add_bug", "edit_scope": "single_line", "solved": 1, "steps": 4},
                {"id": "median_bug", "edit_scope": "multi_line", "solved": 0, "steps": 12},
            ],
        },
        "combined": {
            "aggregate": {"solved": 1.0, "tests_passed": 1.0, "used_search_notes": 1.0},
            "by_category": {
                "knowledge_to_config": {"solved": 1.0},
                "knowledge_to_policy": {"solved": 1.0},
            },
        },
    }


def test_generate_eval_plots(tmp_path) -> None:
    paths = generate_plots(_sample_report(), tmp_path)
    names = {p.name for p in paths}
    assert names == {
        "docqa_overview.svg",
        "docqa_by_category.svg",
        "code_overview.svg",
        "code_by_difficulty.svg",
        "code_by_edit_scope.svg",
        "code_steps_by_task.svg",
        "combined_overview.svg",
        "combined_by_category.svg",
    }
    for path in paths:
        text = path.read_text()
        assert text.startswith("<svg")
        assert "</svg>" in text


def test_load_explicit_report(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_sample_report()))
    report, path = load_report(report_path)
    assert path == report_path
    assert report["code"]["aggregate"]["solved"] == 0.6
