from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RETRIEVAL = ROOT / "research/qatelier/experiments/s1_baseline_lock/scientific_retrieval"


def test_scifact_definition_and_external_preparation_are_hash_linked():
    data = json.loads((RETRIEVAL / "data_manifest.json").read_text())
    split = json.loads((RETRIEVAL / "split_manifest.json").read_text())
    validation = json.loads((RETRIEVAL / "artifacts/preparation_validation.json").read_text())
    assert data["members"]["corpus"]["rows"] == 5183
    assert data["members"]["queries"]["rows"] == 1109
    assert split["test_qrels_reserved"] is True
    assert validation["corpus_count"] == 5183
    assert validation["query_count"] == 1109
    assert validation["embedding_dimension"] == 768
    assert validation["representations_count"] == 9
    assert validation["provider_contacted"] is False
    assert validation["jobs_submitted"] == 0


def test_scifact_classical_panel_uses_confirmation_only_and_no_test_qrels():
    raw = RETRIEVAL / "raw"
    document = json.loads((raw / "results.json").read_text())
    assert len(document["rows"]) == 360
    assert document["run_manifest"]["test_qrels_used"] is False
    assert document["run_manifest"]["provider_contacted"] is False
    assert document["run_manifest"]["jobs_submitted"] == 0
