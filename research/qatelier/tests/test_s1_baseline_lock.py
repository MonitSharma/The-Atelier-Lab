from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
LOCK = ROOT / "research/qatelier/experiments/s1_baseline_lock/artifacts/baseline_lock.json"


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
