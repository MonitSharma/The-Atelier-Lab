"""Execute the credential-free S0 classical and simulator calibration panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

from research.qatelier.classical import RepresentationMetadata, evaluate, predict, train
from research.qatelier.data.representations import CompressorArtifact, stable_array_hash
from research.qatelier.quantum_adapter import QuantumAdapterConfig, ReadoutSpec
from research.qatelier.simulation import CircuitSchedule, PQCStatevectorSimulator, initialize_parameters
from research.qatelier.experiments.s0_reproduction.splits import load_json


def _digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    return value


def _sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def classification_metrics(labels: np.ndarray, scores: np.ndarray) -> dict[str, float]:
    y = np.asarray(labels, dtype=int)
    values = np.asarray(scores, dtype=float)
    predictions = (values >= 0.0).astype(int)
    probabilities = _sigmoid(values)
    recalls = [
        float(np.mean(predictions[y == label] == label))
        for label in (0, 1)
        if np.any(y == label)
    ]
    log_loss = -float(np.mean(y * np.log(np.clip(probabilities, 1e-12, 1.0)) + (1 - y) * np.log(np.clip(1 - probabilities, 1e-12, 1.0))))
    return {
        "accuracy": float(np.mean(predictions == y)),
        "balanced_accuracy": float(np.mean(recalls)),
        "brier_score": float(np.mean((probabilities - y) ** 2)),
        "log_loss": log_loss,
    }


def _load_prepared(prepared_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]], np.ndarray, list[str]]:
    manifest = load_json(prepared_dir / "preparation_manifest.json")
    examples = {
        (item["source_member"], int(item["row_index"])): item
        for item in json.loads((prepared_dir / "examples.json").read_text())
    }
    with np.load(prepared_dir / "embeddings.npz", allow_pickle=False) as payload:
        sample_ids = [str(value) for value in payload["sample_ids"].tolist()]
        embeddings = np.asarray(payload["embeddings"], dtype=np.float32)
    if stable_array_hash(embeddings) != manifest["embeddings_hash"]:
        raise ValueError("prepared embedding cache hash does not match preparation manifest")
    if len(sample_ids) != len(examples) or len(set(sample_ids)) != len(sample_ids):
        raise ValueError("prepared sample IDs are not unique and aligned")
    return manifest, examples, embeddings, sample_ids


def _ids_for_indices(
    examples: dict[tuple[str, int], dict[str, Any]], member: str, indices: Iterable[int]
) -> list[str]:
    ids = []
    for row_index in indices:
        try:
            ids.append(examples[(member, int(row_index))]["sample_id"])
        except KeyError as exc:
            raise ValueError(f"prepared cache is missing {member}[{row_index}]") from exc
    return ids


def _features(
    sample_ids: list[str],
    *,
    embeddings: np.ndarray,
    cached_sample_ids: list[str],
    compressor: CompressorArtifact,
) -> np.ndarray:
    lookup = {sample_id: index for index, sample_id in enumerate(cached_sample_ids)}
    try:
        values = embeddings[[lookup[sample_id] for sample_id in sample_ids]]
    except KeyError as exc:
        raise ValueError(f"prepared cache is missing sample ID: {exc.args[0]}") from exc
    return compressor.transform(values)


def _labels(examples: dict[tuple[str, int], dict[str, Any]], member: str, indices: Iterable[int]) -> np.ndarray:
    return np.asarray([examples[(member, int(index))]["label"] for index in indices], dtype=int)


def _load_compressor(prepared_dir: Path, manifest: dict[str, Any], seed: int, budget: int) -> CompressorArtifact:
    records = [record for record in manifest["compressors"] if record["seed"] == seed and record["budget_per_class"] == budget]
    if len(records) != 1:
        raise ValueError(f"expected exactly one compressor for seed={seed}, budget={budget}")
    return CompressorArtifact.load(prepared_dir / records[0]["path"])


def _quantum_scores(simulator: PQCStatevectorSimulator, features: np.ndarray, parameters: np.ndarray, *, shots: int | None = None, seed: int | None = None) -> np.ndarray:
    values = []
    for index, row in enumerate(features):
        row_seed = None if seed is None else seed + index
        values.append(simulator.run(row, parameters, shots=shots, seed=row_seed).expectations[0])
    return np.asarray(values, dtype=float)


def _quantum_loss(simulator: PQCStatevectorSimulator, features: np.ndarray, labels: np.ndarray, parameters: np.ndarray, l2: float) -> float:
    scores = _quantum_scores(simulator, features, parameters)
    return float(np.mean(np.logaddexp(0.0, scores) - labels * scores) + l2 * np.mean(parameters * parameters))


def _train_quantum(
    config: QuantumAdapterConfig,
    features: np.ndarray,
    labels: np.ndarray,
    *,
    seed: int,
    steps: int,
    learning_rate: float,
    epsilon: float,
    l2: float,
    initialization_scale: float,
) -> tuple[np.ndarray, list[dict[str, float]]]:
    if steps < 1 or learning_rate <= 0 or epsilon <= 0 or l2 < 0:
        raise ValueError("invalid quantum training configuration")
    simulator = PQCStatevectorSimulator(config)
    parameters = initialize_parameters(config, seed=seed, scale=initialization_scale)
    history: list[dict[str, float]] = []
    for step in range(steps):
        current_loss = _quantum_loss(simulator, features, labels, parameters, l2)
        gradient = np.zeros_like(parameters)
        for index in range(parameters.size):
            plus = parameters.copy()
            minus = parameters.copy()
            plus[index] += epsilon
            minus[index] -= epsilon
            gradient[index] = (
                _quantum_loss(simulator, features, labels, plus, l2)
                - _quantum_loss(simulator, features, labels, minus, l2)
            ) / (2.0 * epsilon)
        gradient = np.clip(gradient, -5.0, 5.0)
        parameters -= learning_rate * gradient
        history.append({"step": float(step), "loss": current_loss, "gradient_norm": float(np.linalg.norm(gradient))})
    history.append({"step": float(steps), "loss": _quantum_loss(simulator, features, labels, parameters, l2), "gradient_norm": 0.0})
    return parameters, history


def _classical_config(name: str, q: int) -> dict[str, Any]:
    return {
        "logistic": {"max_iter": 1000},
        "linear_svm": {"max_iter": 2000},
        "rbf_svm": {},
        "polynomial_svm": {"degree": 2},
        "rff": {"n_features": max(8, 2 * q), "gamma": 1.0},
        "matched_mlp": {"hidden_layers": (8,), "max_iter": 60, "learning_rate": 0.05},
        "low_rank_bilinear": {"rank": 1, "max_iter": 60, "learning_rate": 0.03},
        "finite_rbf": {"n_centers": min(8, 2 * q), "gamma": 1.0},
    }[name]


def _fit_classical(name: str, train_x: np.ndarray, train_y: np.ndarray, *, seed: int, representation: RepresentationMetadata, q: int):
    return train(name, train_x, train_y, seed=seed, representation=representation, **_classical_config(name, q))


def _classical_record(model: Any, eval_x: np.ndarray, eval_y: np.ndarray, *, representation: RepresentationMetadata) -> dict[str, Any]:
    metrics = evaluate(model, eval_x, eval_y, representation=representation)
    probabilities = predict(model, eval_x, return_proba=True)
    score = probabilities[:, 1]
    return {
        "model_type": "classical",
        "candidate_id": model.name,
        "model_metadata": model.to_metadata(),
        "metrics": {**metrics, "brier_score": float(np.mean((score - eval_y) ** 2))},
        "scores_hash": stable_array_hash(score),
    }


def _quantum_record(
    family: str,
    q: int,
    reuploads: int,
    eval_x: np.ndarray,
    eval_y: np.ndarray,
    *,
    confirmation_seed: int,
    protocol: dict[str, Any],
    circuit_config: QuantumAdapterConfig,
    parameters: np.ndarray,
    history: list[dict[str, float]],
) -> dict[str, Any]:
    simulator = PQCStatevectorSimulator(circuit_config)
    exact_scores = _quantum_scores(simulator, eval_x, parameters)
    finite_scores = _quantum_scores(simulator, eval_x, parameters, shots=int(protocol["finite_shots"]), seed=confirmation_seed)
    schedule = CircuitSchedule.from_config(circuit_config)
    return {
        "model_type": "quantum_simulator",
        "candidate_id": f"{family}-q{q}-R{reuploads}",
        "circuit": schedule.to_dict(),
        "parameters_hash": stable_array_hash(parameters),
        "training_seed": None,
        "confirmation_seed": confirmation_seed,
        "training_history": history,
        "exact": {"metrics": classification_metrics(eval_y, exact_scores), "scores_hash": stable_array_hash(exact_scores)},
        "finite_shot": {"shots": int(protocol["finite_shots"]), "seed": confirmation_seed, "metrics": classification_metrics(eval_y, finite_scores), "scores_hash": stable_array_hash(finite_scores)},
    }


def run_s0(
    *,
    config_path: str | Path,
    prepared_dir: str | Path,
    output_dir: str | Path,
    selection_limit: int | None = None,
    candidate_limit: int | None = None,
) -> Path:
    """Run S0 with fixed splits and no cloud/provider access."""

    config_path = Path(config_path)
    prepared = Path(prepared_dir)
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S0 raw output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(config_path.read_text())
    manifest, examples, embeddings, sample_ids = _load_prepared(prepared)
    split = load_json(config_path.parent / "split_manifest.json")
    train_member = split["train_member"]
    confirmation_member = split["confirmation_member"]
    train_selections = [(int(seed), int(budget), indices) for seed, budgets in split["train_row_indices"].items() for budget, indices in budgets.items()]
    train_selections.sort(key=lambda item: (item[0], item[1]))
    if selection_limit is not None:
        train_selections = train_selections[:selection_limit]
    candidates = [(family, int(q), int(reuploads)) for family in config["protocol"]["quantum_families"] for q in config["protocol"]["quantum_qubits"] for reuploads in config["protocol"]["quantum_reuploads"]]
    if candidate_limit is not None:
        candidates = candidates[:candidate_limit]
    confirmation_seeds = [int(seed) for seed in split["confirmation_seeds"]]
    rows: list[dict[str, Any]] = []
    for train_seed, budget, train_indices in train_selections:
        compressor = _load_compressor(prepared, manifest, train_seed, budget)
        train_ids = _ids_for_indices(examples, train_member, train_indices)
        train_labels = _labels(examples, train_member, train_indices)
        for q in sorted(set([candidate[1] for candidate in candidates])):
            train_x = _features(train_ids, embeddings=embeddings, cached_sample_ids=sample_ids, compressor=compressor)[:, :q]
            representation = RepresentationMetadata(
                representation_id=manifest["embeddings_hash"],
                dimension=q,
                compressor_id=f"s0-seed-{train_seed}-budget-{budget}",
                compressor_hash=compressor.artifact_hash,
                split_id=f"train-{train_seed}-{budget}",
                normalization="none",
                source="s0-prepared-mpnet",
            )
            classical_models = {
                name: _fit_classical(name, train_x, train_labels, seed=train_seed, representation=representation, q=q)
                for name in config["protocol"]["classical_controls"]
            }
            quantum_fits = []
            for family, candidate_q, reuploads in candidates:
                if candidate_q != q:
                    continue
                circuit_config = QuantumAdapterConfig(
                    q=q,
                    R=reuploads,
                    L=1,
                    family=family,
                    readout=ReadoutSpec(("Z0",), trainable_weights=True, trainable_bias=True),
                )
                initialization_seed = train_seed * 10000 + q * 100 + reuploads * 10 + (0 if family == "QIA-P" else 1)
                parameters, history = _train_quantum(
                    circuit_config,
                    train_x,
                    train_labels,
                    seed=initialization_seed,
                    steps=int(config["protocol"]["quantum_train_steps"]),
                    learning_rate=float(config["protocol"]["quantum_learning_rate"]),
                    epsilon=float(config["protocol"]["quantum_finite_difference_epsilon"]),
                    l2=float(config["protocol"]["quantum_l2"]),
                    initialization_scale=float(config["protocol"]["quantum_initialization_scale"]),
                )
                quantum_fits.append((family, q, reuploads, circuit_config, parameters, history, initialization_seed))
            for confirmation_seed in confirmation_seeds:
                confirmation_indices = split["confirmation_row_indices"][str(confirmation_seed)]
                confirmation_ids = _ids_for_indices(examples, confirmation_member, confirmation_indices)
                confirmation_labels = _labels(examples, confirmation_member, confirmation_indices)
                eval_x = _features(confirmation_ids, embeddings=embeddings, cached_sample_ids=sample_ids, compressor=compressor)[:, :q]
                representation = RepresentationMetadata(
                    representation_id=manifest["embeddings_hash"],
                    dimension=q,
                    compressor_id=f"s0-seed-{train_seed}-budget-{budget}",
                    compressor_hash=compressor.artifact_hash,
                    split_id=f"train-{train_seed}-{budget}",
                    normalization="none",
                    source="s0-prepared-mpnet",
                )
                for name, model in classical_models.items():
                    rows.append({"train_seed": train_seed, "budget_per_class": budget, "confirmation_seed": confirmation_seed, "q": q, "representation": representation.to_dict(), **_classical_record(model, eval_x, confirmation_labels, representation=representation)})
                for family, candidate_q, reuploads, circuit_config, parameters, history, initialization_seed in quantum_fits:
                    record = _quantum_record(family, q, reuploads, eval_x, confirmation_labels, confirmation_seed=confirmation_seed, protocol=config["protocol"], circuit_config=circuit_config, parameters=parameters, history=history)
                    record["training_seed"] = initialization_seed
                    rows.append({"train_seed": train_seed, "budget_per_class": budget, "q": q, **record})
    run_manifest = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        "preparation_manifest_sha256": hashlib.sha256((prepared / "preparation_manifest.json").read_bytes()).hexdigest(),
        "selection_limit": selection_limit,
        "candidate_limit": candidate_limit,
        "provider_contacted": False,
        "jobs_submitted": 0,
        "execution_modes": ["exact_numpy_statevector", "finite_shot_numpy_statevector"],
        "row_count": len(rows),
        "status": "partial_smoke" if selection_limit is not None or candidate_limit is not None else "completed",
    }
    (destination / "run_manifest.json").write_text(json.dumps(_json_ready(run_manifest), indent=2, sort_keys=True) + "\n")
    (destination / "results.json").write_text(json.dumps(_json_ready({"schema_version": 1, "run_manifest": run_manifest, "rows": rows}), indent=2, sort_keys=True) + "\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prepared-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--selection-limit", type=int)
    parser.add_argument("--candidate-limit", type=int)
    args = parser.parse_args()
    destination = run_s0(
        config_path=args.config,
        prepared_dir=args.prepared_dir,
        output_dir=args.output_dir,
        selection_limit=args.selection_limit,
        candidate_limit=args.candidate_limit,
    )
    print(json.dumps({"status": "completed", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
