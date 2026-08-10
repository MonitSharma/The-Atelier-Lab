from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_current_phase_audit_is_negative_and_provider_free():
    document = json.loads((ROOT / "research/qatelier/audit_artifacts/audit.json").read_text())
    assert document["status"] == "negative_result_audited_current_phase"
    assert document["provider_contacted"] is False
    assert document["jobs_submitted"] == 0
    assert document["physical_quantinuum_jobs"] == 0
    assert document["frozen_candidates"] == []
    assert document["hardware_authorized"] is False
    assert document["c1_c4_claim_supported"] is False
