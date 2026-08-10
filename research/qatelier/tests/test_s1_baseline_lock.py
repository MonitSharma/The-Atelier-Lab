from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
LOCK = ROOT / "research/qatelier/experiments/s1_baseline_lock/artifacts/baseline_lock.json"
LOCK_ALL = ROOT / "research/qatelier/experiments/s1_baseline_lock/artifacts/baseline_lock_all.json"


def test_s1_lock_is_hash_linked_and_explicitly_partial():
    document = json.loads(LOCK.read_text())
    assert document["status"] == "sst2_reference_locked_only"
    assert document["claim_level"] == "classical_reference"
    assert document["source_s0_raw_sha256"]
    assert len(document["summaries"]) == 16
    assert set(document["unresolved_s1_tasks"]) == {
        "semantic_pair",
        "additional_classification",
        "scientific_retrieval",
        "controlled_interaction_order",
    }


def test_s1_multitask_lock_has_three_reference_tasks_and_no_jobs():
    document = json.loads(LOCK_ALL.read_text())
    assert document["status"] == "partial_multitask_reference_lock"
    assert document["claim_level"] == "classical_reference"
    assert len(document["summaries"]) == 32
    assert {record["task"] for record in document["summaries"]} == {"sst2", "mrpc", "cola"}
    assert set(document["unresolved_s1_tasks"]) == {"controlled_interaction_order"}
    for task in ("mrpc", "cola"):
        record = next(record for record in document["source_records"] if record["task"] == task)
        assert record["row_count"] == 480
    assert next(record for record in document["source_records"] if record["task"] == "scientific_retrieval")["row_count"] == 360
    assert next(record for record in document["source_records"] if record["task"] == "controlled_interaction_order")["row_count"] == 14400


def test_s1_archived_public_task_panels_are_classical_only_and_complete():
    base = LOCK_ALL.parent.parent / "raw"
    expected_candidates = {
        "rbf_svm", "polynomial_svm", "logistic", "linear_svm", "rff",
        "matched_mlp", "low_rank_bilinear", "finite_rbf",
    }
    for task in ("mrpc", "cola"):
        document = json.loads((base / task / "results.json").read_text())
        assert len(document["rows"]) == 480
        assert document["run_manifest"]["provider_contacted"] is False
        assert document["run_manifest"]["jobs_submitted"] == 0
        assert {row["candidate_id"] for row in document["rows"]} == expected_candidates
