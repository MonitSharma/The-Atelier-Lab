"""Run the representation-matched classical S1 panel for MRPC or CoLA."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from research.qatelier.classical import RepresentationMetadata, evaluate, train
from research.qatelier.data.representations import CompressorArtifact, stable_array_hash


def _model_config(name: str) -> dict[str, Any]:
    return {
        "logistic": {},
        "linear_svm": {},
        "rbf_svm": {},
        "polynomial_svm": {"degree": 2},
        "rff": {"n_features": 8, "gamma": 1.0},
        "matched_mlp": {"hidden_layers": (8,), "max_iter": 60},
        "low_rank_bilinear": {"rank": 1, "max_iter": 60},
        "finite_rbf": {"n_centers": 8, "gamma": 1.0},
    }[name]


def _load_prepared(path: Path) -> tuple[dict[str, Any], dict[tuple[str, int], dict[str, Any]], np.ndarray, list[str]]:
    manifest = json.loads((path / "preparation_manifest.json").read_text())
    examples = json.loads((path / ("pair_examples.json" if (path / "pair_examples.json").exists() else "examples.json")).read_text())
    by_key = {(item["member" if "member" in item else "source_member"], int(item["row_index"])): item for item in examples}
    with np.load(path / ("pair_embeddings.npz" if (path / "pair_embeddings.npz").exists() else "embeddings.npz"), allow_pickle=False) as payload:
        sample_ids = [str(value) for value in payload["sample_ids"].tolist()]
        features = np.asarray(payload["features"] if "features" in payload else payload["embeddings"], dtype=np.float32)
        labels = np.asarray(payload["labels"], dtype=int) if "labels" in payload else None
    if stable_array_hash(features) != manifest["pair_features_hash" if "pair_features_hash" in manifest else "embeddings_hash"]:
        raise ValueError("prepared feature cache hash does not match its manifest")
    if labels is not None:
        for sample_id, item in zip(sample_ids, examples):
            if int(item["label"]) != int(labels[sample_ids.index(sample_id)]):
                raise ValueError("prepared labels are not aligned with sample IDs")
    return manifest, by_key, features, sample_ids


def _ids(by_key: dict[tuple[str, int], dict[str, Any]], member: str, indices: list[int]) -> list[str]:
    return [by_key[(member, int(index))]["sample_id"] for index in indices]


def _labels(by_key: dict[tuple[str, int], dict[str, Any]], member: str, indices: list[int]) -> np.ndarray:
    return np.asarray([by_key[(member, int(index))]["label"] for index in indices], dtype=int)


def run_classical(*, config_path: str | Path, task: str, prepared_dir: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    task_config = config["pair_task"] if task == "mrpc" else config["additional_classification"]
    root = config_path.parent
    split = json.loads((root / task_config["split_manifest"]).read_text())
    prepared = Path(prepared_dir)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S1 output must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    manifest, by_key, features, sample_ids = _load_prepared(prepared)
    train_member = split["train_member"]
    confirmation_member = split["confirmation_member"]
    index_lookup = {sample_id: index for index, sample_id in enumerate(sample_ids)}
    rows: list[dict[str, Any]] = []
    for train_seed, selections in split["train_row_indices"].items():
        for budget, train_indices in selections.items():
            compressor_records = [record for record in manifest["compressors"] if record["seed"] == int(train_seed) and record["budget_per_class"] == int(budget)]
            if len(compressor_records) != 1:
                raise ValueError("prepared task does not contain exactly one matching compressor")
            compressor = CompressorArtifact.load(prepared / compressor_records[0]["path"])
            train_ids = _ids(by_key, train_member, train_indices)
            train_x = compressor.transform(features[[index_lookup[sample_id] for sample_id in train_ids]])
            representation = RepresentationMetadata(f"{task}-{manifest['pair_features_hash'] if 'pair_features_hash' in manifest else manifest['embeddings_hash']}", train_x.shape[1], compressor_id=f"{task}-seed-{train_seed}-budget-{budget}", compressor_hash=compressor.artifact_hash, split_id=f"train-{train_seed}-{budget}", source=f"s1-{task}")
            train_y = _labels(by_key, train_member, train_indices)
            models = {name: train(name, train_x, train_y, seed=int(train_seed), representation=representation, **_model_config(name)) for name in config["baseline_groups"]["strong_reference"] + config["baseline_groups"]["parameter_matched"]}
            for confirmation_seed, confirmation_indices in split["confirmation_row_indices"].items():
                confirmation_ids = _ids(by_key, confirmation_member, confirmation_indices)
                eval_x = compressor.transform(features[[index_lookup[sample_id] for sample_id in confirmation_ids]])
                eval_y = _labels(by_key, confirmation_member, confirmation_indices)
                for name, model in models.items():
                    metrics = evaluate(model, eval_x, eval_y, representation=representation)
                    rows.append({"task": task, "train_seed": int(train_seed), "budget_per_class": int(budget), "confirmation_seed": int(confirmation_seed), "model_type": "classical", "candidate_id": name, "q": int(eval_x.shape[1]), "representation": representation.to_dict(), "metrics": metrics, "model_metadata": model.to_metadata()})
    run_manifest = {"schema_version": 1, "experiment_id": config["experiment_id"], "task": task, "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "preparation_manifest_sha256": hashlib.sha256((prepared / "preparation_manifest.json").read_bytes()).hexdigest(), "row_count": len(rows), "provider_contacted": False, "jobs_submitted": 0, "status": "completed"}
    (destination / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    (destination / "results.json").write_text(json.dumps({"run_manifest": run_manifest, "rows": rows}, indent=2, sort_keys=True) + "\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--task", choices=("mrpc", "cola"), required=True)
    parser.add_argument("--prepared-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = run_classical(config_path=args.config, task=args.task, prepared_dir=args.prepared_dir, output_dir=args.output_dir)
    print(json.dumps({"status": "completed", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
