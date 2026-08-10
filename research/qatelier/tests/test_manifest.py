from __future__ import annotations

from research.qatelier.manifest import ExperimentManifest, make_result_envelope


def _manifest() -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="interaction-order-smoke",
        question="Does interaction order change the head ranking?",
        hypothesis="Higher-order targets expose different inductive biases.",
        changed_variable="interaction_order",
        controls=("logistic", "rbf", "quantum"),
        datasets=("synthetic_gaussian",),
        seeds=(0, 1),
        software={"python": "3.11", "numpy": "2"},
        metadata={"q": 4},
    )


def test_manifest_hash_is_stable_and_sensitive_to_controls() -> None:
    manifest = _manifest()
    assert manifest.manifest_hash == _manifest().manifest_hash
    changed = ExperimentManifest(**{**manifest.to_dict(), "changed_variable": "depth"})
    assert changed.manifest_hash != manifest.manifest_hash


def test_result_envelope_keeps_provenance_and_metrics() -> None:
    result = make_result_envelope(
        _manifest(),
        metrics={"accuracy": 0.75},
        artifacts=["results.json"],
        observation="smoke run",
        limitations=["not hardware validated"],
        reproduction_command="python -m qatelier.run",
        timestamp="2026-08-10T00:00:00+00:00",
    )
    assert result["manifest_hash"] == _manifest().manifest_hash
    assert result["metrics"]["accuracy"] == 0.75
    assert result["manifest"]["seeds"] == [0, 1]
