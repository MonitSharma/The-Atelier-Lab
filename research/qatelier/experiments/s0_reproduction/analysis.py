"""Analyze the immutable S0 raw result bundle without test-set tuning."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def _mean_std(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "mean": float(np.mean(array)),
        "std": float(np.std(array, ddof=1)) if array.size > 1 else 0.0,
    }


def _bootstrap_ci(values: list[float], *, seed: int = 20260810, replicates: int = 2000) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    if array.size == 0:
        raise ValueError("cannot bootstrap an empty set")
    rng = np.random.default_rng(seed)
    samples = rng.choice(array, size=(replicates, array.size), replace=True).mean(axis=1)
    return {
        "mean": float(array.mean()),
        "lower_95": float(np.quantile(samples, 0.025)),
        "upper_95": float(np.quantile(samples, 0.975)),
        "replicates": replicates,
        "seed": seed,
    }


def _load_results(raw_directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    results_path = raw_directory / "results.json"
    if not results_path.is_file():
        raise FileNotFoundError(f"S0 raw result bundle does not exist: {results_path}")
    document = json.loads(results_path.read_text())
    manifest = document.get("run_manifest", {})
    if manifest.get("status") != "completed":
        raise ValueError("S0 analysis requires an unbounded completed raw run")
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("S0 raw result bundle contains no rows")
    return document, rows


def _metric(row: dict[str, Any], metric: str, condition: str = "exact") -> float:
    if row["model_type"] == "quantum_simulator":
        return float(row[condition]["metrics"][metric])
    return float(row["metrics"][metric])


def _row_key(row: dict[str, Any]) -> tuple[int, int, int, int]:
    return (int(row["train_seed"]), int(row["budget_per_class"]), int(row["confirmation_seed"]), int(row["q"]))


def analyze_s0(*, config_path: str | Path, raw_directory: str | Path, output_directory: str | Path) -> Path:
    config_path = Path(config_path)
    raw = Path(raw_directory)
    destination = Path(output_directory)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S0 analysis output directory must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    document, rows = _load_results(raw)
    config = yaml.safe_load(config_path.read_text())
    split = json.loads((config_path.parent / "split_manifest.json").read_text())
    selection_count = sum(len(budgets) for budgets in split["train_row_indices"].values())
    confirmation_count = len(split["confirmation_seeds"])
    q_count = len(config["protocol"]["quantum_qubits"])
    candidate_count = len(config["protocol"]["quantum_families"]) * q_count * len(config["protocol"]["quantum_reuploads"])
    expected_rows = selection_count * confirmation_count * (q_count * len(config["protocol"]["classical_controls"]) + candidate_count)
    if len(rows) != expected_rows:
        raise ValueError(f"S0 row count mismatch: {len(rows)} != {expected_rows}")
    if document["run_manifest"].get("provider_contacted") is not False or document["run_manifest"].get("jobs_submitted") != 0:
        raise ValueError("S0 raw bundle violates the credential-free execution invariant")

    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault((row["model_type"], row["candidate_id"], int(row["q"])), []).append(row)
    summaries = []
    for (model_type, candidate_id, q), group in sorted(groups.items()):
        summary = {
            "model_type": model_type,
            "candidate_id": candidate_id,
            "q": q,
            "exact_accuracy": _mean_std([_metric(row, "accuracy") for row in group]),
            "exact_balanced_accuracy": _mean_std([_metric(row, "balanced_accuracy") for row in group]),
        }
        if model_type == "quantum_simulator":
            exact = np.asarray([_metric(row, "accuracy") for row in group])
            finite = np.asarray([_metric(row, "accuracy", "finite_shot") for row in group])
            summary["finite_shot_accuracy"] = _mean_std(finite.tolist())
            summary["finite_minus_exact_accuracy"] = _mean_std((finite - exact).tolist())
        summaries.append(summary)

    logistic = {_row_key(row): row for row in rows if row["model_type"] == "classical" and row["candidate_id"] == "logistic"}
    paired = []
    for row in rows:
        if row["model_type"] != "quantum_simulator":
            continue
        baseline = logistic.get(_row_key(row))
        if baseline is None:
            raise ValueError(f"missing paired logistic baseline for {row['candidate_id']} and key {_row_key(row)}")
        paired.append(
            {
                "candidate_id": row["candidate_id"],
                "q": int(row["q"]),
                "train_seed": int(row["train_seed"]),
                "budget_per_class": int(row["budget_per_class"]),
                "confirmation_seed": int(row["confirmation_seed"]),
                "exact_accuracy_delta_vs_logistic": _metric(row, "accuracy") - _metric(baseline, "accuracy"),
                "finite_accuracy_delta_vs_logistic": _metric(row, "accuracy", "finite_shot") - _metric(baseline, "accuracy"),
            }
        )
    paired_summary = []
    for candidate_id in sorted({item["candidate_id"] for item in paired}):
        subset = [item for item in paired if item["candidate_id"] == candidate_id]
        exact = [item["exact_accuracy_delta_vs_logistic"] for item in subset]
        finite = [item["finite_accuracy_delta_vs_logistic"] for item in subset]
        paired_summary.append({"candidate_id": candidate_id, "q": subset[0]["q"], "exact_accuracy_delta": _bootstrap_ci(exact), "finite_accuracy_delta": _bootstrap_ci(finite, seed=20260811)})

    learning_curve = []
    for (model_type, candidate_id, q), group in sorted(groups.items()):
        for budget in sorted({int(row["budget_per_class"]) for row in group}):
            subset = [row for row in group if int(row["budget_per_class"]) == budget]
            learning_curve.append({"model_type": model_type, "candidate_id": candidate_id, "q": q, "budget_per_class": budget, "exact_accuracy": _mean_std([_metric(row, "accuracy") for row in subset])})

    analysis = {
        "schema_version": 1,
        "status": "s0_calibration_analysis",
        "scientific_claim_level": "calibration_only",
        "raw_results_sha256": hashlib.sha256((raw / "results.json").read_bytes()).hexdigest(),
        "row_count": len(rows),
        "expected_row_count": expected_rows,
        "selection_count": selection_count,
        "confirmation_seed_count": confirmation_count,
        "quantum_candidate_count": candidate_count,
        "provider_contacted": False,
        "jobs_submitted": 0,
        "summaries": summaries,
        "paired_quantum_vs_logistic": paired_summary,
        "learning_curve": learning_curve,
    }
    (destination / "analysis.json").write_text(json.dumps(analysis, indent=2, sort_keys=True) + "\n")
    lines = [
        "# S0 calibration analysis",
        "",
        "This is a preregistered calibration report, not evidence of quantum advantage.",
        "",
        f"- Raw rows: {len(rows)} / expected {expected_rows}",
        f"- Confirmation seeds: {confirmation_count}",
        f"- Provider contact: {analysis['provider_contacted']}",
        f"- Jobs submitted: {analysis['jobs_submitted']}",
        "",
        "## Candidate summaries",
        "",
        "| Type | Candidate | q | Exact accuracy mean ± std | Finite-shot accuracy mean ± std |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        finite = summary.get("finite_shot_accuracy")
        finite_text = "—" if finite is None else f"{finite['mean']:.4f} ± {finite['std']:.4f}"
        exact = summary["exact_accuracy"]
        lines.append(f"| {summary['model_type']} | {summary['candidate_id']} | {summary['q']} | {exact['mean']:.4f} ± {exact['std']:.4f} | {finite_text} |")
    lines.extend(["", "Paired deltas are against the logistic baseline on the same training selection, confirmation seed, and compressed representation. Bootstrap intervals are descriptive calibration intervals; they do not establish a C1/C2 claim.", ""])
    (destination / "analysis.md").write_text("\n".join(lines))
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-directory", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    destination = analyze_s0(config_path=args.config, raw_directory=args.raw_directory, output_directory=args.output_directory)
    print(json.dumps({"status": "analyzed", "output_directory": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
