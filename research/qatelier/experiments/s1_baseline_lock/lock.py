"""Freeze the SST-2 classical reference table from the completed S0 bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import yaml


def _mean_std(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {"n": int(array.size), "mean": float(array.mean()), "std": float(array.std(ddof=1))}


def lock_sst2(*, config_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    source = config_path.parent / config["source_s0"]["raw_results"]
    completion = config_path.parent / config["source_s0"]["completion_manifest"]
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S1 lock output must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    if not source.is_file() or not completion.is_file():
        raise FileNotFoundError("S1 requires the completed S0 raw bundle and completion manifest")
    completion_document = json.loads(completion.read_text())
    raw_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    if raw_sha256 != completion_document["raw_results_sha256"]:
        raise ValueError("S0 raw results do not match the committed completion manifest")
    document = json.loads(source.read_text())
    rows = document["rows"]
    classical = [row for row in rows if row["model_type"] == "classical"]
    required = set(config["baseline_groups"]["strong_reference"] + config["baseline_groups"]["parameter_matched"])
    observed = {row["candidate_id"] for row in classical}
    if observed != required:
        raise ValueError(f"S1 classical catalogue mismatch: {sorted(observed)} != {sorted(required)}")
    expected_n = len(config["protocol"]["training_selection_seeds"]) * len(config["protocol"]["budgets_per_class"]) * len(config["protocol"]["confirmation_seeds"])
    summaries = []
    for candidate in sorted(required):
        for q in (2, 4):
            subset = [row for row in classical if row["candidate_id"] == candidate and int(row["q"]) == q]
            if len(subset) != expected_n:
                raise ValueError(f"S1 row count mismatch for {candidate}, q={q}: {len(subset)} != {expected_n}")
            values = [float(row["metrics"][config["protocol"]["metric"]]) for row in subset]
            summaries.append({"candidate_id": candidate, "q": q, "capacity_group": "strong_reference" if candidate in config["baseline_groups"]["strong_reference"] else "parameter_matched", "metric": config["protocol"]["metric"], "aggregate": _mean_std(values)})
    lock = {
        "schema_version": 1,
        "status": "sst2_reference_locked_only",
        "claim_level": "classical_reference",
        "source_s0_raw_sha256": raw_sha256,
        "source_s0_completion_sha256": hashlib.sha256(completion.read_bytes()).hexdigest(),
        "test_tuning_allowed": False,
        "public_task_status": config["public_tasks"],
        "baseline_groups": config["baseline_groups"],
        "summaries": summaries,
        "unresolved_s1_tasks": [name for name, task in config["public_tasks"].items() if task["status"] != "locked_from_s0"],
    }
    (destination / "baseline_lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    lines = [
        "# S1 classical baseline lock",
        "",
        "Status: SST-2 reference locked; full multi-task S1 remains incomplete.",
        "",
        "This artifact is derived from the completed S0 raw bundle. It performs no retraining, confirmation-seed selection, or test tuning.",
        "",
        "| Group | Candidate | q | Mean accuracy | Sample std | n |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        aggregate = summary["aggregate"]
        lines.append(f"| {summary['capacity_group']} | {summary['candidate_id']} | {summary['q']} | {aggregate['mean']:.4f} | {aggregate['std']:.4f} | {aggregate['n']} |")
    lines.extend(["", "Unresolved S1 tasks: " + ", ".join(lock["unresolved_s1_tasks"]) + ".", ""])
    (destination / "baseline_lock.md").write_text("\n".join(lines))
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = lock_sst2(config_path=args.config, output_dir=args.output_dir)
    print(json.dumps({"status": "locked_sst2", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
