"""Non-bypassable provider execution guards for the current QAtelier phase."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


HELIOS_1E_EMULATOR = "Helios-1E"


class HardwarePolicyError(RuntimeError):
    """Raised when a provider request violates the frozen QAtelier policy."""


@dataclass(frozen=True)
class QuantinuumPolicy:
    """The only Quantinuum execution policy permitted in this phase."""

    allowed_backends: tuple[str, ...] = (HELIOS_1E_EMULATOR,)
    physical_execution_allowed: bool = False
    syntax_check_required: bool = True
    cost_check_required: bool = True

    def validate_backend(self, backend: str) -> None:
        if backend not in self.allowed_backends:
            raise HardwarePolicyError(
                f"Quantinuum execution blocked: only {self.allowed_backends[0]} emulator is allowed; "
                f"received {backend!r}"
            )

    def validate_submission(
        self,
        *,
        backend: str,
        physical_execution: bool,
        cost_manifest: str | Path | None,
        logical_circuit_hash: str,
        configuration_hash: str,
    ) -> dict[str, Any]:
        """Validate a would-be submission without contacting a provider."""

        self.validate_backend(backend)
        if physical_execution or not self.physical_execution_allowed:
            if physical_execution:
                raise HardwarePolicyError(
                    "Quantinuum physical execution is disabled for the current QAtelier phase"
                )
        if self.syntax_check_required or self.cost_check_required:
            if cost_manifest is None:
                raise HardwarePolicyError(
                    "Quantinuum execution blocked: syntax/resource cost check required"
                )
            artifact = _read_cost_manifest(cost_manifest)
            _validate_cost_manifest(
                artifact,
                backend=backend,
                logical_circuit_hash=logical_circuit_hash,
                configuration_hash=configuration_hash,
            )
        return {"backend": backend, "physical_execution": False, "cost_manifest": str(cost_manifest)}


def _read_cost_manifest(path: str | Path) -> Mapping[str, Any]:
    manifest_path = Path(path)
    try:
        payload = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise HardwarePolicyError(f"invalid Quantinuum cost manifest: {manifest_path}") from exc
    if not isinstance(payload, Mapping):
        raise HardwarePolicyError("Quantinuum cost manifest must be a JSON object")
    return payload


def _validate_cost_manifest(
    payload: Mapping[str, Any], *, backend: str, logical_circuit_hash: str, configuration_hash: str
) -> None:
    required = (
        "logical_circuit_hash",
        "compiled_circuit_hash",
        "configuration_hash",
        "backend",
        "syntax_checker_result",
        "estimated_HQC_cost",
        "checker_backend",
        "checker_timestamp",
        "qubits",
        "shots",
        "logical_1q_gates",
        "logical_2q_gates",
        "compiled_1q_gates",
        "compiled_2q_gates",
        "compiled_depth",
        "measurement_count",
        "requested_repetitions",
        "software_versions",
    )
    missing = [key for key in required if key not in payload]
    if missing:
        raise HardwarePolicyError("cost manifest missing required fields: " + ", ".join(missing))
    if payload["backend"] != backend or payload["checker_backend"] != backend:
        raise HardwarePolicyError("cost manifest backend does not match the requested Helios-1E target")
    if payload["logical_circuit_hash"] != logical_circuit_hash:
        raise HardwarePolicyError("cost manifest does not match the exact logical circuit")
    if payload["configuration_hash"] != configuration_hash:
        raise HardwarePolicyError("cost manifest does not match the exact circuit configuration")
    if payload["syntax_checker_result"] != "accepted":
        raise HardwarePolicyError("Quantinuum execution blocked: syntax checker did not accept the circuit")
    if payload.get("physical_hardware_allowed") is not False:
        raise HardwarePolicyError("cost manifest must explicitly disable physical Quantinuum hardware")
    cost = payload["estimated_HQC_cost"]
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost < 0:
        raise HardwarePolicyError("estimated_HQC_cost must be a non-negative number")
    if not payload["checker_timestamp"]:
        raise HardwarePolicyError("cost manifest must include checker_timestamp")


def hash_configuration(configuration: Mapping[str, Any]) -> str:
    """Return a stable full SHA-256 hash for cost-manifest identity."""

    canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


__all__ = [
    "HELIOS_1E_EMULATOR",
    "HardwarePolicyError",
    "QuantinuumPolicy",
    "hash_configuration",
]
