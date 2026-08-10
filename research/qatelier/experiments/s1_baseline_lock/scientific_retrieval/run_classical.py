"""Run the representation-matched S1 SciFact retrieval reference panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from research.qatelier.classical import RepresentationMetadata, predict, train
from research.qatelier.data.representations import make_pair_representation


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


def _metric(scores: np.ndarray, relevant: set[str], corpus_ids: list[str]) -> dict[str, float]:
    order = np.argsort(-scores, kind="stable")[:10]
    ranked = [corpus_ids[int(index)] for index in order]
    hits = [int(document_id in relevant) for document_id in ranked]
    dcg = sum(value / np.log2(index + 2) for index, value in enumerate(hits))
    ideal = sum(1.0 / np.log2(index + 2) for index in range(min(10, len(relevant))))
    first = next((index + 1 for index, value in enumerate(hits) if value), None)
    return {
        "ndcg_at_10": float(dcg / ideal) if ideal else 0.0,
        "mrr_at_10": float(1.0 / first) if first else 0.0,
        "recall_at_10": float(sum(hits) / len(relevant)) if relevant else 0.0,
    }


def _pair_features(query: np.ndarray, documents: np.ndarray) -> np.ndarray:
    return make_pair_representation(
        np.repeat(query.reshape(1, -1), len(documents), axis=0), documents
    )


def run_classical(*, config_path: str | Path, prepared_dir: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    prepared_dir = Path(prepared_dir)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"retrieval output must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    config = __import__("yaml").safe_load(config_path.read_text())
    root = config_path.parent
    split = json.loads((root / config["sources"]["split_manifest"]).read_text())
    preparation = json.loads((prepared_dir / "preparation_manifest.json").read_text())
    with np.load(prepared_dir / "embeddings.npz", allow_pickle=False) as embeddings:
        corpus_ids = [str(value) for value in embeddings["corpus_ids"].tolist()]
        query_ids = [str(value) for value in embeddings["query_ids"].tolist()]
    corpus_index = {value: index for index, value in enumerate(corpus_ids)}
    query_index = {value: index for index, value in enumerate(query_ids)}
    train_qrels = json.loads((prepared_dir / "qrels_train.json").read_text())
    rng_base = 91000
    rows: list[dict[str, Any]] = []
    for representation_record in preparation["representations"]:
        train_seed = int(representation_record["train_seed"])
        budget = int(representation_record["budget"])
        with np.load(prepared_dir / representation_record["features"], allow_pickle=False) as features:
            corpus_features = np.asarray(features["corpus_features"], dtype=np.float64)
            query_features = np.asarray(features["query_features"], dtype=np.float64)
        selected_queries = [str(value) for value in split["training_query_ids"][str(train_seed)][str(budget)]]
        positives = [(query_id, document_id) for query_id in selected_queries for document_id in train_qrels[query_id]]
        positive_lookup = {query_id: set(train_qrels[query_id]) for query_id in selected_queries}
        negative_pairs: list[tuple[str, str]] = []
        rng = np.random.default_rng(rng_base + train_seed * 100 + budget)
        for query_id in selected_queries:
            pool = rng.permutation(len(corpus_ids))
            chosen = 0
            for index in pool:
                document_id = corpus_ids[int(index)]
                if document_id not in positive_lookup[query_id]:
                    negative_pairs.append((query_id, document_id))
                    chosen += 1
                    if chosen == 4:
                        break
        train_pairs = positives + negative_pairs
        query_matrix = query_features[[query_index[query_id] for query_id, _ in train_pairs]]
        document_matrix = corpus_features[[corpus_index[document_id] for _, document_id in train_pairs]]
        x_train = np.concatenate((query_matrix, document_matrix, np.abs(query_matrix - document_matrix), query_matrix * document_matrix), axis=1)
        y_train = np.asarray([1] * len(positives) + [0] * len(negative_pairs), dtype=int)
        representation = RepresentationMetadata(
            representation_id=f"scifact-seed-{train_seed}-budget-{budget}",
            dimension=x_train.shape[1],
            compressor_id=f"seed-{train_seed}-budget-{budget}",
            compressor_hash=representation_record["compressor_metadata"]["artifact_hash"],
            split_id=f"train-{train_seed}-budget-{budget}",
            source="s1-scifact-frozen-pair-representation",
        )
        models = {name: train(name, x_train, y_train, seed=train_seed, representation=representation, **options) for name, options in MODELS}
        for confirmation_seed, selected_confirmation in split["confirmation_query_ids"].items():
            for name, model in models.items():
                metrics = []
                for query_id in selected_confirmation:
                    query = query_features[query_index[str(query_id)]]
                    pair_x = _pair_features(query, corpus_features)
                    scores = predict(model, pair_x, return_proba=True)[:, 1]
                    metrics.append(_metric(scores, set(train_qrels[str(query_id)]), corpus_ids))
                rows.append({"task": "scifact", "train_seed": train_seed, "budget": budget, "confirmation_seed": int(confirmation_seed), "model_type": "classical", "candidate_id": name, "representation": representation.to_dict(), "training_pair_count": len(train_pairs), "confirmation_query_count": len(metrics), "metrics": {key: float(np.mean([item[key] for item in metrics])) for key in metrics[0]}, "metric_std_over_queries": {key: float(np.std([item[key] for item in metrics], ddof=1)) for key in metrics[0]}})
    run_manifest = {"schema_version": 1, "experiment_id": config["experiment_id"], "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "preparation_manifest_sha256": hashlib.sha256((prepared_dir / "preparation_manifest.json").read_bytes()).hexdigest(), "row_count": len(rows), "provider_contacted": False, "jobs_submitted": 0, "test_qrels_used": False, "status": "completed_classical_reference_panel"}
    (output_dir / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n")
    (output_dir / "results.json").write_text(json.dumps({"run_manifest": run_manifest, "rows": rows}, indent=2, sort_keys=True) + "\n")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prepared-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = run_classical(config_path=args.config, prepared_dir=args.prepared_dir, output_dir=args.output_dir)
    print(json.dumps({"status": "completed", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
