import json

from models.router.make_planner_dataset import build


def test_planner_dataset_builds_from_eval_metadata() -> None:
    summary = build()

    assert summary["docqa"] >= 18
    assert summary["code"] >= 13
    assert summary["combined"] >= 10
    assert summary["rows"] == summary["docqa"] + summary["code"] + summary["combined"]
    assert summary["mlx_lora_data_dir"].endswith("models/router/planner_data")


def test_planner_dataset_rows_have_expected_json_shape() -> None:
    summary = build()
    path = summary["path"]

    with open(path, encoding="utf-8") as handle:
        row = json.loads(next(handle))

    completion = json.loads(row["completion"].strip())
    assert set(completion) == {
        "category",
        "difficulty",
        "edit_scope",
        "tool_plan",
        "model_route",
    }
    assert isinstance(completion["tool_plan"], list)
