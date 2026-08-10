from __future__ import annotations

import json
from pathlib import Path

from research.qatelier.experiments.s0_reproduction.splits import select_stratified_indices


ROOT = Path(__file__).parents[3]
S0 = ROOT / "research/qatelier/experiments/s0_reproduction"


def _rows() -> list[dict[str, str]]:
    return [{"sentence": f"row-{index}", "label": str(index % 2)} for index in range(300)]


def test_stratified_selection_is_deterministic_and_balanced():
    rows = _rows()
    first = select_stratified_indices(rows, seed=11, budget_per_class=16)
    second = select_stratified_indices(rows, seed=11, budget_per_class=16)
    assert first == second
    assert len(first) == 32
    assert sum(rows[index]["label"] == "0" for index in first) == 16
    assert sum(rows[index]["label"] == "1" for index in first) == 16


def test_committed_s0_split_manifest_has_all_declared_selections():
    split = json.loads((S0 / "split_manifest.json").read_text())
    assert set(split["train_row_indices"]) == {"11", "13", "17"}
    for selections in split["train_row_indices"].values():
        assert set(selections) == {"16", "32", "64", "128"}
        assert [len(selections[str(budget)]) for budget in (16, 32, 64, 128)] == [2 * budget for budget in (16, 32, 64, 128)]
    assert len(split["confirmation_row_indices"]) == 128
