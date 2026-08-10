"""Trace-friendly local performance measurements."""

from __future__ import annotations

import platform
import resource
import shutil
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

from atelier.config import settings


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


def system_snapshot() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        peak_memory_mib = round(usage / (1024 * 1024), 2)
    else:
        peak_memory_mib = round((usage * 1024) / (1024 * 1024), 2)
    disk = shutil.disk_usage(settings.home_dir)
    return {"platform": platform.platform(), "python": platform.python_version(),
            "runtime_home": str(settings.home_dir), "free_disk_gib": round(disk.free / 1024**3, 3),
            "total_disk_gib": round(disk.total / 1024**3, 3), "peak_process_memory_mib": peak_memory_mib}


def service_baseline(service: Any, *, repetitions: int = 1) -> dict[str, Any]:
    samples = [measure("service.health.cold", service.health)]
    for _ in range(max(1, repetitions)):
        samples.extend([
            measure("service.health", service.health),
            measure("service.workflows", service.workflows),
            measure("service.library", service.library),
            measure("service.route", lambda: service.route("analyze this CSV dataset")),
        ])
    return {"platform": platform.platform(), "python": platform.python_version(),
            "samples": [sample.to_dict() for sample in samples],
            "all_ok": all(sample.ok for sample in samples), "system": system_snapshot()}
