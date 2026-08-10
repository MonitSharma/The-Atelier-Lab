from __future__ import annotations

import json
from pathlib import Path

from research.qatelier.experiments.s0_reproduction.execution import classification_metrics


ROOT = Path(__file__).parents[3]
S0 = ROOT / "research/qatelier/experiments/s0_reproduction"


def test_committed_s0_raw_bundle_has_the_complete_declared_grid():
    document = json.loads((S0 / "raw/results.json").read_text())
    rows = document["rows"]
    assert document["run_manifest"]["status"] == "completed"
    assert len(rows) == 1440
    assert sum(row["model_type"] == "quantum_simulator" for row in rows) == 480
    assert sum(row["model_type"] == "classical" for row in rows) == 960
    assert document["run_manifest"]["provider_contacted"] is False
    assert document["run_manifest"]["jobs_submitted"] == 0


def test_classification_metrics_are_bounded_and_deterministic():
    first = classification_metrics([0, 1, 1, 0], [-1.0, 1.0, 0.0, -0.5])
    second = classification_metrics([0, 1, 1, 0], [-1.0, 1.0, 0.0, -0.5])
    assert first == second
    assert 0.0 <= first["accuracy"] <= 1.0
    assert 0.0 <= first["balanced_accuracy"] <= 1.0
    assert 0.0 <= first["brier_score"] <= 1.0
