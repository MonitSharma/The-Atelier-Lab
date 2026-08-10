from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
RAW = ROOT / "research/qatelier/experiments/s2_mechanism_screen/raw/results.json"


def test_s2_archived_screen_contains_diagnostics_and_no_provider_jobs():
    document = json.loads(RAW.read_text())
    rows = document["rows"]
    assert len(rows) == 112
    assert sum(row["model_type"] == "quantum_simulator" for row in rows) == 64
    assert all("gradient_summary" in row for row in rows if row["model_type"] == "quantum_simulator")
    assert all("line_spectral_summary" in row for row in rows if row["model_type"] == "quantum_simulator")
    assert document["run_manifest"]["provider_contacted"] is False
    assert document["run_manifest"]["jobs_submitted"] == 0
