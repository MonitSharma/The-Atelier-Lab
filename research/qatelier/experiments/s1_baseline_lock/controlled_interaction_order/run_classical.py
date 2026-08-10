"""Run the frozen classical head panel on the controlled-order S1 bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from research.qatelier.classical import RepresentationMetadata, evaluate, train


MODELS = (
    ("rbf_svm", {}),
    ("polynomial_svm", {"degree": 2}),
    ("logistic", {}),
    ("linear_svm", {}),
    ("rff", {"n_features": 8, "gamma": 1.0}),
    ("matched_mlp", {"hidden_layers": (8,), "max_iter": 60}),
    ("low_rank_bilinear", {"rank": 1, "max_iter": 60}),
    ("finite_rbf", {"n_centers": 8, "gamma": 1.0}),
)


def run_classical(*, artifact_dir: str | Path, output_dir: str | Path) -> Path:
    artifact_dir = Path(artifact_dir)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"S1 output must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((artifact_dir / "manifest.json").read_text())
    with np.load(artifact_dir / manifest["data"]["path"], allow_pickle=False) as bundle:
        features = np.asarray(bundle["features"], dtype=np.float64)
        labels = np.asarray(bundle["labels"], dtype=np.int8)
    if features.shape != (192, 512, 6) or labels.shape != (192, 512):
        raise ValueError("unexpected controlled-order bundle dimensions")

    records = manifest["splits"]
    by_key = {(record["problem_id"], record["kind"], int(record["seed"])): record for record in records}
    rows: list[dict[str, Any]] = []
    for record in records:
        if record["kind"] != "train":
            continue
        problem_id = record["problem_id"]
        train_seed = int(record["seed"])
        train_features = features[int(record["data_index"])]
        train_labels = labels[int(record["data_index"])]
        for budget_text, selection in record["budget_selection_indices"].items():
            budget = int(budget_text)
            x_train = train_features[np.asarray(selection, dtype=int)]
            y_train = train_labels[np.asarray(selection, dtype=int)]
            representation = RepresentationMetadata(
                representation_id=f"s1-controlled-{problem_id}",
                dimension=x_train.shape[1],
                split_id=f"train-{train_seed}-budget-{budget}",
                source="s1-controlled-interaction-order",
            )
            models = {
                name: train(name, x_train, y_train, seed=train_seed, representation=representation, **options)
                for name, options in MODELS
            }
            for confirmation_seed in (101, 103, 107, 109, 113):
                confirmation = by_key[(problem_id, "confirmation", confirmation_seed)]
                x_eval = features[int(confirmation["data_index"])]
                y_eval = labels[int(confirmation["data_index"])]
                for name, model in models.items():
                    rows.append(
                        {
                            "task": "controlled_interaction_order",
                            "problem_id": problem_id,
                            "family": record["family"],
                            "order": int(record["order"]),
                            "train_seed": train_seed,
                            "budget_per_class": budget,
                            "confirmation_seed": confirmation_seed,
                            "model_type": "classical",
                            "candidate_id": name,
                            "representation": representation.to_dict(),
                            "metrics": evaluate(model, x_eval, y_eval, representation=representation),
                            "train_split_fingerprint": record["split_fingerprint"],
                            "confirmation_split_fingerprint": confirmation["split_fingerprint"],
                        }
                    )
    run_manifest = {
        "schema_version": 1,
        "experiment_id": "qatelier-s1-controlled-interaction-order-classical",
        "artifact_manifest_sha256": hashlib.sha256((artifact_dir / "manifest.json").read_bytes()).hexdigest(),
        "row_count": len(rows),
        "provider_contacted": False,
        "jobs_submitted": 0,
        "status": "completed_classical_reference_panel",
    }
    (output_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    (output_dir / "results.json").write_text(json.dumps({"run_manifest": run_manifest, "rows": rows}, indent=2, sort_keys=True) + "\n")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = run_classical(artifact_dir=args.artifact_dir, output_dir=args.output_dir)
    print(json.dumps({"status": "completed", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
