from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
RAW = ROOT / "research/qatelier/experiments/s2_mechanism_screen/raw/results.json"
ORDERS = ROOT / "research/qatelier/experiments/s2_mechanism_screen/raw/orders_1_6_fair"
FREEZE = ROOT / "research/qatelier/experiments/s2_mechanism_screen/analysis/candidate_freeze.json"


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
    assert len(document["rows"]) == 528
    assert sum(row["model_type"] == "classical" for row in document["rows"]) == 144
    assert all(row["feature_projection"] == "first_q_features" for row in document["rows"])
    assert len({(row["q"], row["train_feature_matrix_sha256"], row["evaluation_feature_matrix_sha256"]) for row in document["rows"]}) == 2
    for q in (2, 4):
        by_type = {
            model_type: {row["train_feature_matrix_sha256"] for row in document["rows"] if row["q"] == q and row["model_type"] == model_type}
            for model_type in ("classical", "quantum_simulator")
        }
        assert all(len(hashes) == 1 for hashes in by_type.values())
        assert by_type["classical"] == by_type["quantum_simulator"]
    assert validation["orders"] == [1, 2, 3, 4, 5, 6]
    assert validation["q_values"] == [2, 4]
    assert validation["quantum_families"] == ["QIA-A", "QIA-L", "QIA-P", "QIA-X"]
    assert validation["candidate_freeze"] is False
    assert validation["provider_contacted"] is False
    assert validation["jobs_submitted"] == 0


def test_s2_candidate_gate_freezes_nothing_and_authorizes_no_hardware():
    decision = json.loads(FREEZE.read_text())
    assert decision["status"] == "no_candidate_frozen_exploratory_negative"
    assert decision["frozen_candidates"] == []
    assert decision["hardware_authorized"] is False
    assert decision["c4_claim_supported"] is False
    assert decision["provider_contacted"] is False
    assert decision["jobs_submitted"] == 0
