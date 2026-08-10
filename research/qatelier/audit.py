"""Build the credential-free QAtelier audit manifest for the current phase."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_audit(*, output_dir: str | Path) -> Path:
    destination = Path(output_dir)
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"audit output must be new and empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    s0 = ROOT / "experiments/s0_reproduction"
    s1 = ROOT / "experiments/s1_baseline_lock"
    s2 = ROOT / "experiments/s2_mechanism_screen"
    s3 = ROOT / "experiments/s3_heldout"
    completion = json.loads((s0 / "s0_completion.json").read_text())
    if _sha256(s0 / "raw/results.json") != completion["raw_results_sha256"]:
        raise ValueError("S0 completion hash mismatch")
    provider_records: list[dict[str, Any]] = []
    raw_paths = [
        s1 / "raw/mrpc/run_manifest.json",
        s1 / "raw/cola/run_manifest.json",
        s1 / "scientific_retrieval/raw/run_manifest.json",
        s1 / "controlled_interaction_order/raw/run_manifest.json",
        s2 / "raw/run_manifest.json",
        s2 / "raw/orders_1_6/run_manifest.json",
        s2 / "raw/orders_1_6_fair/run_manifest.json",
    ]
    for path in raw_paths:
        manifest = json.loads(path.read_text())
        if manifest.get("provider_contacted") or manifest.get("jobs_submitted"):
            raise ValueError(f"provider activity found in {path}")
        provider_records.append({"path": str(path.relative_to(ROOT)), "sha256": _sha256(path), "row_count": manifest.get("row_count", 0)})
    freeze = json.loads((s2 / "analysis/candidate_freeze.json").read_text())
    if freeze["frozen_candidates"] or freeze["hardware_authorized"]:
        raise ValueError("candidate freeze artifact unexpectedly authorizes hardware")
    s3_decision = json.loads((s3 / "decision.json").read_text())
    if s3_decision["test_data_used"] or s3_decision["provider_contacted"] or s3_decision["jobs_submitted"]:
        raise ValueError("S3 decision unexpectedly reports execution")
    required_release_files = [
        ROOT / "FINAL_RESEARCH_REPORT.md",
        ROOT / "manuscript/qatelier_draft.md",
        ROOT / "manuscript/REPRODUCIBILITY_APPENDIX.md",
        ROOT / "hardware/HARDWARE_DECISIONS.md",
        ROOT / "hardware/PHYSICAL_QUANTINUUM_DECISION.md",
        ROOT / "REQUIREMENTS_AUDIT.md",
    ]
    if any(not path.is_file() for path in required_release_files):
        raise ValueError("release package is incomplete")
    document = {
        "schema_version": 1,
        "status": "negative_result_audited_current_phase",
        "claim_level": "no_quantum_advantage",
        "branch_requirement": "qatelier",
        "s0_completion_sha256": _sha256(s0 / "s0_completion.json"),
        "s1_multitask_lock_sha256": _sha256(s1 / "artifacts/baseline_lock_all.json"),
        "s2_candidate_freeze_sha256": _sha256(s2 / "analysis/candidate_freeze.json"),
        "s3_decision_sha256": _sha256(s3 / "decision.json"),
        "requirements_audit_sha256": _sha256(ROOT / "REQUIREMENTS_AUDIT.md"),
        "final_report_sha256": _sha256(ROOT / "FINAL_RESEARCH_REPORT.md"),
        "manuscript_sha256": _sha256(ROOT / "manuscript/qatelier_draft.md"),
        "hardware_decisions_sha256": _sha256(ROOT / "hardware/HARDWARE_DECISIONS.md"),
        "provider_records": provider_records,
        "preflight_contacted": True,
        "provider_contacted": False,
        "jobs_submitted": 0,
        "physical_quantinuum_jobs": 0,
        "frozen_candidates": [],
        "hardware_authorized": False,
        "c1_c4_claim_supported": False,
        "reproduction_commands": [
            ".venv/bin/pytest -q research/qatelier/tests",
            ".venv/bin/python scripts/validate_experiments.py",
        ],
    }
    (destination / "audit.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    lines = [
        "# QAtelier current-phase audit",
        "",
        "Status: negative result audited; no quantum advantage or hardware utility claim is supported.",
        "",
        "The S0 calibration, S1 classical reference panels, fair-projection S2 mechanism screen, and no-candidate freeze are hash-linked. Read-only provider discovery was performed, but every archived scientific execution manifest records zero provider jobs. Quantinuum physical jobs: 0.",
        "",
        "Frozen candidates: none.",
        "Hardware authorized: false.",
        "C1–C4 claim supported: false.",
        "",
        "Reproduction commands:",
        "",
        "```bash",
        ".venv/bin/pytest -q research/qatelier/tests",
        ".venv/bin/python scripts/validate_experiments.py",
        "```",
        "",
    ]
    (destination / "audit.md").write_text("\n".join(lines))
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    destination = build_audit(output_dir=args.output_dir)
    print(json.dumps({"status": "audited", "output_dir": str(destination)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
