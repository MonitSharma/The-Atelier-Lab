"""Reproducible metadata primitives for QAtelier experiments.

The research branch records configuration and provenance alongside numerical
results.  This module deliberately uses only the standard library so metadata
can be created before optional ML or quantum packages are installed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ExperimentManifest:
    """Immutable identity and controls for one experiment family."""

    experiment_id: str
    question: str
    hypothesis: str
    changed_variable: str
    controls: tuple[str, ...] = ()
    datasets: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()
    software: dict[str, str] = field(default_factory=dict)
    hardware: str = "local"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["controls"] = list(self.controls)
        payload["datasets"] = list(self.datasets)
        payload["seeds"] = list(self.seeds)
        return payload

    @property
    def manifest_hash(self) -> str:
        """Return a short stable hash suitable for result filenames."""
        digest = hashlib.sha256(_canonical(self.to_dict()).encode("utf-8")).hexdigest()
        return digest[:16]


def make_result_envelope(
    manifest: ExperimentManifest,
    *,
    metrics: dict[str, float] | None = None,
    artifacts: list[str] | None = None,
    observation: str = "",
    limitations: list[str] | None = None,
    reproduction_command: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Create the common JSON envelope used by QAtelier result artifacts."""
    return {
        "experiment_id": manifest.experiment_id,
        "manifest_hash": manifest.manifest_hash,
        "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
        "manifest": manifest.to_dict(),
        "metrics": metrics or {},
        "artifacts": artifacts or [],
        "observation": observation,
        "limitations": limitations or [],
        "reproduction_command": reproduction_command,
    }
