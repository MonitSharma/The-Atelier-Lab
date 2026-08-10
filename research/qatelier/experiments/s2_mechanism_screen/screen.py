"""Run a small controlled interaction-order mechanism screen."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from research.qatelier.benchmark import make_interaction_problem
from research.qatelier.classical import RepresentationMetadata, evaluate, train
from research.qatelier.experiments.s0_reproduction.execution import (
    _quantum_scores,
    _train_quantum,
    classification_metrics,
)
from research.qatelier.mechanisms import centered_kernel_alignment, effective_rank, finite_difference_gradient, gradient_summary, spectral_summary
from research.qatelier.quantum_adapter import QuantumAdapterConfig, ReadoutSpec
from research.qatelier.simulation import CircuitSchedule, PQCStatevectorSimulator


def _ready(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_ready(item) for item in value]
    return value


def _classical_config(name: str) -> dict[str, Any]:
    return {"logistic": {}, "rbf_svm": {}, "matched_mlp": {"hidden_layers": (8,), "max_iter": 60}}[name]


def run_screen(*, config_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S2 output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    problem_config = config["problem"]
    rows: list[dict[str, Any]] = []
    for family in problem_config["families"]:
        for order in problem_config["interaction_orders"]:
            problem = make_interaction_problem(n_features=problem_config["n_features"], interaction_order=order, family=family, problem_seed=problem_config["problem_seed"] + order)
            train_data = problem.sample(problem_config["train_samples"], seed=problem_config["train_seed"])
            evaluation_data = problem.sample(problem_config["evaluation_samples"], seed=problem_config["evaluation_seed"])
            target_kernel = np.outer(2 * train_data.labels - 1, 2 * train_data.labels - 1)
            feature_kernel = train_data.features @ train_data.features.T
            base_diagnostics = {
                "target_definition": dict(problem.target_definition),
                "target_fingerprint": problem.target_fingerprint,
                "train_diagnostics": dict(problem.diagnostics(train_data.features, train_data.labels)),
                "evaluation_diagnostics": dict(problem.diagnostics(evaluation_data.features, evaluation_data.labels)),
                "feature_target_alignment": centered_kernel_alignment(feature_kernel, target_kernel),
                "feature_effective_rank": effective_rank(feature_kernel),
            }
            representation = RepresentationMetadata(f"s2-{problem.target_fingerprint}", problem_config["n_features"], split_id="train-11", source="synthetic-interaction")
            for name in config["classical_controls"]:
                model = train(name, train_data.features, train_data.labels, seed=problem_config["train_seed"], representation=representation, **_classical_config(name))
                rows.append({"family": family, "interaction_order": order, "model_type": "classical", "candidate_id": name, "metrics": evaluate(model, evaluation_data.features, evaluation_data.labels, representation=representation), "target_fingerprint": problem.target_fingerprint, "feature_target_alignment": base_diagnostics["feature_target_alignment"], "feature_effective_rank": base_diagnostics["feature_effective_rank"]})
            for quantum_family in config["quantum"]["families"]:
                for reuploads in config["quantum"]["reuploads"]:
                    for q in config["quantum"]["q_values"]:
                        q = int(q)
                        if q > problem_config["n_features"]:
                            raise ValueError("quantum q cannot exceed benchmark feature dimension")
                        circuit_config = QuantumAdapterConfig(q=q, R=int(reuploads), L=int(config["quantum"]["trainable_layers"]), family=quantum_family, readout=ReadoutSpec(("Z0",), trainable_weights=True, trainable_bias=True))
                        parameters, history = _train_quantum(circuit_config, train_data.features[:, :q], train_data.labels, seed=problem_config["train_seed"] + order, steps=int(config["quantum"]["train_steps"]), learning_rate=float(config["quantum"]["learning_rate"]), epsilon=float(config["quantum"]["finite_difference_epsilon"]), l2=float(config["quantum"]["l2"]), initialization_scale=float(config["quantum"]["initialization_scale"]))
                        simulator = PQCStatevectorSimulator(circuit_config)
                        scores = _quantum_scores(simulator, evaluation_data.features[:, :q], parameters)
                        gradient = finite_difference_gradient(lambda theta: float(np.mean((_quantum_scores(simulator, train_data.features[: int(config["diagnostics"]["gradient_rows"]), :q], theta) - train_data.labels[: int(config["diagnostics"]["gradient_rows"])] ) ** 2)), parameters, epsilon=float(config["diagnostics"]["gradient_epsilon"]))
                        grid = np.linspace(-2.0, 2.0, int(config["diagnostics"]["spectral_grid_size"]))
                        line_features = np.zeros((grid.size, q), dtype=float)
                        line_features[:, 0] = grid
                        line_scores = _quantum_scores(simulator, line_features, parameters)
                        rows.append({"family": family, "interaction_order": order, "model_type": "quantum_simulator", "candidate_id": f"{quantum_family}-q{q}-R{reuploads}", "metrics": classification_metrics(evaluation_data.labels, scores), "target_fingerprint": problem.target_fingerprint, "feature_target_alignment": base_diagnostics["feature_target_alignment"], "feature_effective_rank": base_diagnostics["feature_effective_rank"], "circuit": CircuitSchedule.from_config(circuit_config).to_dict(), "parameters_hash": hashlib.sha256(np.ascontiguousarray(parameters).tobytes()).hexdigest(), "training_history": history, "gradient_summary": gradient_summary(gradient), "line_spectral_summary": spectral_summary(line_scores[:, None])})
    manifest = {"schema_version": 1, "experiment_id": config["experiment_id"], "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(), "row_count": len(rows), "provider_contacted": False, "jobs_submitted": 0, "status": "exploratory_screen_not_selection_freeze"}
    (destination / "run_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (destination / "results.json").write_text(json.dumps(_ready({"run_manifest": manifest, "rows": rows}), indent=2, sort_keys=True) + "\n")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = run_screen(config_path=args.config, output_dir=args.output_dir)
    print(json.dumps({"status": "screened", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
