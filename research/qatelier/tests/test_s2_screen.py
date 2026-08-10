from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
RAW = ROOT / "research/qatelier/experiments/s2_mechanism_screen/raw/results.json"
ORDERS = ROOT / "research/qatelier/experiments/s2_mechanism_screen/raw/orders_1_6"


def test_s2_archived_screen_contains_diagnostics_and_no_provider_jobs():
    document = json.loads(RAW.read_text())
    rows = document["rows"]
    assert len(rows) == 112
    assert sum(row["model_type"] == "quantum_simulator" for row in rows) == 64
    assert all("gradient_summary" in row for row in rows if row["model_type"] == "quantum_simulator")
    assert all("line_spectral_summary" in row for row in rows if row["model_type"] == "quantum_simulator")
    assert document["run_manifest"]["provider_contacted"] is False
    assert document["run_manifest"]["jobs_submitted"] == 0


def test_s2_orders_1_6_panel_covers_all_families_and_orders_without_freezing():
    document = json.loads((ORDERS / "results.json").read_text())
    validation = json.loads((ORDERS / "validation.json").read_text())
    assert len(document["rows"]) == 456
    assert validation["orders"] == [1, 2, 3, 4, 5, 6]
    assert validation["q_values"] == [2, 4]
    assert validation["quantum_families"] == ["QIA-A", "QIA-L", "QIA-P", "QIA-X"]
    assert validation["candidate_freeze"] is False
    assert validation["provider_contacted"] is False
    assert validation["jobs_submitted"] == 0
