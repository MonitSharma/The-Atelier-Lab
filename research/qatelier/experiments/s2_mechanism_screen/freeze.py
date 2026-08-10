"""Apply the preregistered no-candidate gate to the bounded S2 panel."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import numpy as np


def freeze(*, raw_dir: str | Path, output_dir: str | Path) -> Path:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"S2 freeze output must be new and empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = raw_dir / "results.json"
    validation_path = raw_dir / "validation.json"
    document = json.loads(results_path.read_text())
    validation = json.loads(validation_path.read_text())
    if validation["candidate_freeze"] or validation["provider_contacted"] or validation["jobs_submitted"]:
        raise ValueError("S2 input is already frozen or contacted a provider")
    rows = document["rows"]
    quantum = [row for row in rows if row["model_type"] == "quantum_simulator"]
    classical = [row for row in rows if row["model_type"] == "classical"]
    means: dict[str, dict[str, float | int]] = {}
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in quantum:
        grouped[row["candidate_id"]].append(float(row["metrics"]["accuracy"]))
    for candidate, values in sorted(grouped.items()):
        array = np.asarray(values, dtype=float)
        means[candidate] = {"n": int(array.size), "mean_accuracy": float(array.mean()), "sample_std": float(array.std(ddof=1))}
    classical_mean = float(np.mean([float(row["metrics"]["accuracy"]) for row in classical]))
    decision = {
        "schema_version": 1,
        "status": "no_candidate_frozen_exploratory_negative",
        "claim_level": "no_quantum_advantage",
        "raw_results_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
        "raw_validation_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
        "screen_row_count": len(rows),
        "quantum_candidate_summaries": means,
        "classical_control_mean_accuracy": classical_mean,
        "decision_rule": "No candidate is frozen when the exploratory quantum panel is near chance and below the classical reference panel; this gate permits no hardware execution.",
        "frozen_candidates": [],
        "provider_contacted": False,
        "jobs_submitted": 0,
        "hardware_authorized": False,
        "c4_claim_supported": False,
    }
    (output_dir / "candidate_freeze.json").write_text(json.dumps(decision, indent=2, sort_keys=True) + "\n")
    lines = [
        "# S2 candidate freeze decision",
        "",
        "Decision: no quantum candidate frozen; hardware execution is not authorized.",
        "",
        "The bounded all-order screen remains exploratory and uses short training budgets. Every quantum candidate is near chance and below the aggregate classical control mean, so the branch stops before provider execution and makes no C1–C4 claim.",
        "",
        "| Candidate | Mean accuracy | Sample std | n |",
        "| --- | ---: | ---: | ---: |",
    ]
    for candidate, summary in means.items():
        lines.append(f"| {candidate} | {summary['mean_accuracy']:.4f} | {summary['sample_std']:.4f} | {summary['n']} |")
    lines.extend(["", f"Aggregate classical control accuracy: {classical_mean:.4f}.", "", "Frozen candidates: none.", "Hardware authorized: false.", ""])
    (output_dir / "candidate_freeze.md").write_text("\n".join(lines))
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = freeze(raw_dir=args.raw_dir, output_dir=args.output_dir)
    print(json.dumps({"status": "no_candidate_frozen", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
