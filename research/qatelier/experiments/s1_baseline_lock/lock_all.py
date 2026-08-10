"""Aggregate the frozen S1 reference tables across the prepared public tasks."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml


def _aggregate(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=float)
    return {
        "n": int(array.size),
        "mean": float(array.mean()),
        "std": float(array.std(ddof=1)),
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _summaries(
    rows: list[dict[str, Any]],
    *,
    task: str,
    required: set[str],
    expected_n: int,
    q_values: set[int],
    metric: str,
    groups: dict[str, list[str]],
) -> list[dict[str, Any]]:
    observed = {row["candidate_id"] for row in rows}
    if observed != required:
        raise ValueError(f"{task} classical catalogue mismatch: {sorted(observed)} != {sorted(required)}")
    result = []
    for candidate in sorted(required):
        for q in sorted(q_values):
            subset = [
                row
                for row in rows
                if row["candidate_id"] == candidate and int(row["q"]) == q
            ]
            if len(subset) != expected_n:
                raise ValueError(
                    f"{task} row count mismatch for {candidate}, q={q}: "
                    f"{len(subset)} != {expected_n}"
                )
            group = next(name for name, members in groups.items() if candidate in members)
            result.append(
                {
                    "task": task,
                    "candidate_id": candidate,
                    "q": q,
                    "capacity_group": group,
                    "metric": metric,
                    "aggregate": _aggregate([float(row["metrics"][metric]) for row in subset]),
                }
            )
    return result


def lock_all(*, config_path: str | Path, output_dir: str | Path) -> Path:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text())
    root = config_path.parent
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"S1 lock output must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    groups = config["baseline_groups"]
    required = set(groups["strong_reference"] + groups["parameter_matched"])
    metric = config["protocol"]["metric"]
    expected_n = (
        len(config["protocol"]["training_selection_seeds"])
        * len(config["protocol"]["budgets_per_class"])
        * len(config["protocol"]["confirmation_seeds"])
    )
    summaries: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []

    s0_path = root / config["source_s0"]["raw_results"]
    completion_path = root / config["source_s0"]["completion_manifest"]
    completion = json.loads(completion_path.read_text())
    if _sha256(s0_path) != completion["raw_results_sha256"]:
        raise ValueError("S0 raw results do not match its completion manifest")
    s0_rows = [row for row in json.loads(s0_path.read_text())["rows"] if row["model_type"] == "classical"]
    summaries.extend(
        _summaries(
            s0_rows,
            task="sst2",
            required=required,
            expected_n=expected_n,
            q_values={2, 4},
            metric=metric,
            groups=groups,
        )
    )
    source_records.append({"task": "sst2", "results_sha256": _sha256(s0_path), "row_count": len(s0_rows)})

    for task in ("mrpc", "cola"):
        raw_dir = root / config["raw_results"][task]
        results_path = raw_dir / "results.json"
        manifest_path = raw_dir / "run_manifest.json"
        document = json.loads(results_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if manifest["row_count"] != len(document["rows"]):
            raise ValueError(f"{task} run manifest row count mismatch")
        if manifest["provider_contacted"] or manifest["jobs_submitted"]:
            raise ValueError(f"{task} S1 classical lock unexpectedly contacted a provider")
        summaries.extend(
            _summaries(
                document["rows"],
                task=task,
                required=required,
                expected_n=expected_n,
                q_values={4},
                metric=metric,
                groups=groups,
            )
        )
        source_records.append({"task": task, "results_sha256": _sha256(results_path), "row_count": len(document["rows"])})

    for task in ("scientific_retrieval", "controlled_interaction_order"):
        raw_dir = root / config["raw_results"][task]
        results_path = raw_dir / "results.json"
        manifest_path = raw_dir / "run_manifest.json"
        document = json.loads(results_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if manifest["row_count"] != len(document["rows"]):
            raise ValueError(f"{task} run manifest row count mismatch")
        if manifest["provider_contacted"] or manifest["jobs_submitted"]:
            raise ValueError(f"{task} S1 classical lock unexpectedly contacted a provider")
        source_records.append({"task": task, "results_sha256": _sha256(results_path), "row_count": len(document["rows"])})

    unresolved = [name for name, task in config["public_tasks"].items() if task["status"] not in {"locked_from_s0", "reference_locked"}]
    lock = {
        "schema_version": 1,
        "status": "partial_multitask_reference_lock",
        "claim_level": "classical_reference",
        "config_sha256": _sha256(config_path),
        "source_records": source_records,
        "test_tuning_allowed": False,
        "public_task_status": config["public_tasks"],
        "baseline_groups": groups,
        "summaries": summaries,
        "unresolved_s1_tasks": unresolved,
    }
    (destination / "baseline_lock_all.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    lines = [
        "# S1 classical baseline lock",
        "",
        "Status: SST-2, MRPC, and CoLA reference tables locked; retrieval and controlled-order conditions remain open.",
        "",
        "All rows use frozen train-only representations, fixed confirmation seeds, and no test tuning.",
        "",
        "| Task | Group | Candidate | q | Mean accuracy | Sample std | n |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        aggregate = summary["aggregate"]
        lines.append(
            f"| {summary['task']} | {summary['capacity_group']} | {summary['candidate_id']} | "
            f"{summary['q']} | {aggregate['mean']:.4f} | {aggregate['std']:.4f} | {aggregate['n']} |"
        )
    lines.extend(["", "Unresolved S1 tasks: " + ", ".join(unresolved) + ".", ""])
    (destination / "baseline_lock_all.md").write_text("\n".join(lines))
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = lock_all(config_path=args.config, output_dir=args.output_dir)
    print(json.dumps({"status": "partial_multitask_reference_lock", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
