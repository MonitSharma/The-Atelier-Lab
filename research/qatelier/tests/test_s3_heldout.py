from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
S3 = ROOT / "research/qatelier/experiments/s3_heldout"


def test_s3_ood_protocol_is_locked_but_not_run_without_candidate():
    config = __import__("yaml").safe_load((S3 / "config.yaml").read_text())
    manifest = json.loads((S3 / "ood_manifest.json").read_text())
    decision = json.loads((S3 / "decision.json").read_text())
    assert config["status"] == "preregistered_not_executed_no_candidate"
    assert manifest["revision"] == "e6281661ce1c48d982bc483cf8a173c1bbeb5d31"
    assert manifest["members"]["test"]["rows"] == 25000
    assert decision["ood_protocol_locked"] is True
    assert decision["test_data_used"] is False
    assert decision["quantum_results"] == []
    assert decision["quantinuum_physical_jobs"] == 0
