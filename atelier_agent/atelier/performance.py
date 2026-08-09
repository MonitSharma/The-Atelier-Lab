"""Trace-friendly local performance measurements."""

from __future__ import annotations

import platform
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PerformanceSample:
    operation: str
    elapsed_ms: float
    ok: bool
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def measure(operation: str, function: Callable[[], Any]) -> PerformanceSample:
    started = time.perf_counter()
    try:
        result = function()
    except Exception as exc:  # noqa: BLE001
        return PerformanceSample(operation, round((time.perf_counter() - started) * 1000, 3), False, str(exc))
    detail = str(result)[:200] if result is not None else ""
    return PerformanceSample(operation, round((time.perf_counter() - started) * 1000, 3), True, detail)


def service_baseline(service: Any) -> dict[str, Any]:
    samples = [measure("service.health", service.health), measure("service.workflows", service.workflows), measure("service.library", service.library)]
    return {"platform": platform.platform(), "python": platform.python_version(),
            "samples": [sample.to_dict() for sample in samples],
            "all_ok": all(sample.ok for sample in samples)}
