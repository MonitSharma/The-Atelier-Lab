from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
S1 = ROOT / "research/qatelier/experiments/s1_baseline_lock"


def test_mrpc_manifests_pin_members_and_all_confirmation_seeds():
    data = json.loads((S1 / "mrpc_data_manifest.json").read_text())
    split = json.loads((S1 / "mrpc_split_manifest.json").read_text())
    assert data["members"]["train"]["rows"] == 3668
    assert data["members"]["validation"]["rows"] == 408
    assert set(split["train_row_indices"]) == {"11", "13", "17"}
    assert set(split["confirmation_row_indices"]) == {"101", "103", "107", "109", "113"}
    assert all(len(indices) == 128 for indices in split["confirmation_row_indices"].values())


def test_cola_manifests_pin_members_and_all_confirmation_seeds():
    data = json.loads((S1 / "cola_data_manifest.json").read_text())
    split = json.loads((S1 / "cola_split_manifest.json").read_text())
    assert data["members"]["train"]["rows"] == 8551
    assert data["members"]["validation"]["rows"] == 1043
    assert set(split["train_row_indices"]) == {"11", "13", "17"}
    assert set(split["confirmation_row_indices"]) == {"101", "103", "107", "109", "113"}
