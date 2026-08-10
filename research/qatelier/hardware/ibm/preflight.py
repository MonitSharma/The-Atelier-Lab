"""Non-submitting IBM Quantum preflight utilities.

The module exposes credential presence as booleans only.  Connection and
backend discovery are explicit calls; importing this module never reads a
secret or contacts IBM.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class IBMPreflightError(RuntimeError):
    """Raised when an IBM preflight or frozen-candidate gate fails."""


def _env_keys(path: str | Path) -> set[str]:
    keys: set[str] = set()
    try:
        for line in Path(path).read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            keys.add(stripped.split("=", 1)[0].strip())
    except OSError:
        return set()
    return keys


def credentials_available(path: str | Path = ".env") -> dict[str, bool]:
    """Return IBM credential presence without returning credential values."""

    keys = _env_keys(path)
    return {
        "credentials_available": "QISKIT_IBM_TOKEN" in keys and "QISKIT_IBM_INSTANCE" in keys,
        "token_available": "QISKIT_IBM_TOKEN" in keys,
        "instance_available": "QISKIT_IBM_INSTANCE" in keys,
    }


@dataclass(frozen=True)
class BackendSnapshot:
    name: str
    operational: bool | None
    status: str | None
    pending_jobs: int | None
    num_qubits: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "operational": self.operational,
            "status": self.status,
            "pending_jobs": self.pending_jobs,
            "num_qubits": self.num_qubits,
        }


def connect_from_env(path: str | Path = ".env") -> Any:
    """Create an IBM Runtime service only when explicitly requested."""

    presence = credentials_available(path)
    if not presence["credentials_available"]:
        raise IBMPreflightError("IBM credentials are not available in the requested env file")
    try:
        from dotenv import dotenv_values
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError as exc:  # pragma: no cover - optional provider extra
        raise IBMPreflightError("install the qatelier-ibm extra for IBM preflight") from exc
    values = dotenv_values(path)
    token = values.get("QISKIT_IBM_TOKEN")
    instance = values.get("QISKIT_IBM_INSTANCE")
    if not token or not instance:
        raise IBMPreflightError("IBM credentials are present but incomplete")
    return QiskitRuntimeService(channel="ibm_quantum_platform", token=token, instance=instance)


def backend_snapshot(backend: Any) -> BackendSnapshot:
    """Read status/configuration metadata from a backend without submitting."""

    status = backend.status() if hasattr(backend, "status") else None
    configuration = backend.configuration() if hasattr(backend, "configuration") else None
    return BackendSnapshot(
        name=str(getattr(backend, "name", getattr(backend, "backend_name", "unknown"))),
        operational=getattr(status, "operational", None),
        status=getattr(status, "status_msg", None),
        pending_jobs=getattr(status, "pending_jobs", None),
        num_qubits=getattr(configuration, "num_qubits", None),
    )


def discover_backends(service: Any) -> tuple[BackendSnapshot, ...]:
    """Return non-simulator backend snapshots in provider order."""

    if not hasattr(service, "backends"):
        raise IBMPreflightError("service object does not expose backend discovery")
    return tuple(backend_snapshot(backend) for backend in service.backends(simulator=False))


def require_frozen_candidate(panel: Mapping[str, Any] | None) -> None:
    """Fail closed unless all primary hardware replay locks are present."""

    required = (
        "model_hash", "compressor_hash", "sample_manifest_hash", "circuit_hash",
        "parameters_hash", "shots", "observables", "compilation_policy",
    )
    if not isinstance(panel, Mapping):
        raise IBMPreflightError("IBM hardware execution blocked: frozen candidate panel is missing")
    missing = [key for key in required if panel.get(key) in (None, "", [])]
    if missing:
        raise IBMPreflightError(
            "IBM hardware execution blocked: frozen candidate panel missing " + ", ".join(missing)
        )


__all__ = [
    "BackendSnapshot",
    "IBMPreflightError",
    "backend_snapshot",
    "connect_from_env",
    "credentials_available",
    "discover_backends",
    "require_frozen_candidate",
]
