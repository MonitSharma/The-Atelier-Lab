from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from research.qatelier.experiments.s1_baseline_lock.controlled_interaction_order.generate import (
    DATA_RELATIVE,
    FAMILIES,
    ORDERS,
    validate_artifact,
)


ROOT = Path(__file__).resolve().parents[3]
ARTIFACT = ROOT / "research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order"


def test_controlled_order_manifest_has_complete_matrix_and_frozen_protocol() -> None:
    manifest = json.loads((ARTIFACT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["orders"] == list(ORDERS)
    assert [family["name"] for family in manifest["families"]] == [
        family[0] for family in FAMILIES
    ]
    assert manifest["split_protocol"]["budgets_per_class"] == [16, 32, 64, 128, 256]
    assert manifest["split_protocol"]["confirmation_is_never_used_for_fitting_or_selection"] is True
    assert manifest["provider_safety"] == {"jobs_submitted": 0, "providers_contacted": False}
    assert len(manifest["problems"]) == 24
    assert len(manifest["splits"]) == 192


def test_controlled_order_bundle_validates_without_provider_access() -> None:
    result = validate_artifact(ARTIFACT)
    assert result["status"] == "validated"
    assert result["problem_count"] == 24
    assert result["split_count"] == 192
    assert result["providers_contacted"] is False
    assert result["jobs_submitted"] == 0

    with np.load(ARTIFACT / DATA_RELATIVE, allow_pickle=False) as data:
        assert data["features"].shape == (192, 512, 6)
        assert data["labels"].shape == (192, 512)
        assert set(np.unique(data["labels"])) == {0, 1}


def test_controlled_order_classical_panel_is_complete_and_provider_free() -> None:
    raw = ARTIFACT / "raw"
    document = json.loads((raw / "results.json").read_text())
    assert len(document["rows"]) == 14400
    assert document["run_manifest"]["provider_contacted"] is False
    assert document["run_manifest"]["jobs_submitted"] == 0
    assert {row["candidate_id"] for row in document["rows"]} == {
        "rbf_svm", "polynomial_svm", "logistic", "linear_svm", "rff",
        "matched_mlp", "low_rank_bilinear", "finite_rbf",
    }
