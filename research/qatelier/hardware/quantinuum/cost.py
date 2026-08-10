"""Immutable Quantinuum syntax/resource cost artifacts.

This module does not call a provider.  A future adapter must first translate a
frozen logical circuit into a provider-compatible circuit, obtain the official
syntax/resource response, and persist a :class:`CostCheckManifest`.  The
execution guard then matches that artifact to the exact circuit/configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

from ..policy import HELIOS_1E_EMULATOR, HardwarePolicyError


@dataclass(frozen=True)
class CostCheckManifest:
    experiment_id: str
    candidate_id: str
    logical_circuit_hash: str
    compiled_circuit_hash: str
    configuration_hash: str
    qubits: int
    shots: int
    logical_1q_gates: int
    logical_2q_gates: int
    compiled_1q_gates: int
    compiled_2q_gates: int
    compiled_depth: int
    measurement_count: int
    requested_repetitions: int
    estimated_HQC_cost: float
    checker_backend: str = HELIOS_1E_EMULATOR
    checker_timestamp: str = ""
    software_versions: Mapping[str, str] | None = None
    syntax_checker_result: str = "accepted"
    actual_hqc_cost: float | None = None
    physical_hardware_allowed: bool = False

    def __post_init__(self) -> None:
        if self.checker_backend != HELIOS_1E_EMULATOR:
            raise HardwarePolicyError("Quantinuum cost checks must target the exact Helios-1E emulator")
        if self.physical_hardware_allowed:
            raise HardwarePolicyError("physical Quantinuum hardware is disabled for this phase")
        for name in (
            "qubits", "shots", "logical_1q_gates", "logical_2q_gates",
            "compiled_1q_gates", "compiled_2q_gates", "compiled_depth",
            "measurement_count", "requested_repetitions",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.shots < 1 or self.qubits < 1 or self.requested_repetitions < 1:
            raise ValueError("qubits, shots, and requested_repetitions must be positive")
        if not isinstance(self.estimated_HQC_cost, (int, float)) or self.estimated_HQC_cost < 0:
            raise ValueError("estimated_HQC_cost must be non-negative")
        if self.actual_hqc_cost is not None and self.actual_hqc_cost < 0:
            raise ValueError("actual_hqc_cost must be non-negative when reported")
        if self.syntax_checker_result not in {"accepted", "rejected"}:
            raise ValueError("syntax_checker_result must be accepted or rejected")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["software_versions"] = dict(self.software_versions or {})
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CostCheckManifest":
        return cls(**dict(payload))

    def write_json(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"cost manifest is immutable and already exists: {destination}")
        destination.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n")
        return destination

    def write_report(self, path: str | Path, *, campaign: str, candidates: int, samples_per_candidate: int) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise FileExistsError(f"cost report is immutable and already exists: {destination}")
        actual = "not reported"
        lines = [
            "# QAtelier Quantinuum pre-execution cost report",
            "",
            f"Campaign: {campaign}",
            f"Backend: {self.checker_backend}",
            f"Candidates: {candidates}",
            f"Samples per candidate: {samples_per_candidate}",
            f"Shots per repetition: {self.shots}",
            "",
            "## Candidate estimate",
            "",
            f"- Candidate: `{self.candidate_id}`",
            f"- Estimated HQC cost: `{self.estimated_HQC_cost}`",
            f"- Actual charged cost if reported: `{actual if self.actual_hqc_cost is None else self.actual_hqc_cost}`",
            "",
            "Physical Quantinuum jobs: DISABLED",
            "",
            "Execution decision: APPROVED FOR HELIOS-1E EMULATOR ONLY after the exact cost manifest is verified.",
        ]
        destination.write_text("\n".join(lines) + "\n")
        return destination


def validate_cost_manifest(
    path: str | Path,
    *,
    backend: str = HELIOS_1E_EMULATOR,
    logical_circuit_hash: str,
    configuration_hash: str,
) -> CostCheckManifest:
    """Load and verify an accepted exact-match cost artifact."""

    if backend != HELIOS_1E_EMULATOR:
        raise HardwarePolicyError("only the Helios-1E emulator is allowed")
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HardwarePolicyError(f"invalid Quantinuum cost manifest: {manifest_path}") from exc
    manifest = CostCheckManifest.from_dict(payload)
    if manifest.checker_backend != backend:
        raise HardwarePolicyError("cost manifest backend mismatch")
    if manifest.logical_circuit_hash != logical_circuit_hash:
        raise HardwarePolicyError("cost manifest does not match the exact logical circuit")
    if manifest.configuration_hash != configuration_hash:
        raise HardwarePolicyError("cost manifest does not match the exact configuration")
    if manifest.syntax_checker_result != "accepted":
        raise HardwarePolicyError("execution blocked: Quantinuum syntax checker rejected the circuit")
    if not manifest.checker_timestamp:
        raise HardwarePolicyError("cost manifest must include checker_timestamp")
    return manifest


def now_utc() -> str:
    """Return a timezone-aware checker timestamp for a new artifact."""

    return datetime.now(timezone.utc).isoformat()


__all__ = ["CostCheckManifest", "now_utc", "validate_cost_manifest"]
