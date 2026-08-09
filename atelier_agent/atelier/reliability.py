"""Small, dependency-free reliability reporting primitives."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable


def wilson_interval(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    if trials <= 0 or successes < 0 or successes > trials:
        raise ValueError("successes must be between zero and trials")
    rate = successes / trials
    denominator = 1 + z * z / trials
    center = (rate + z * z / (2 * trials)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z * z / (4 * trials)) / trials) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def summarize_trials(rows: Iterable[dict[str, Any]], suite: str = "unnamed") -> dict[str, Any]:
    records = list(rows)
    successes = sum(bool(row.get("success")) for row in records)
    trials = len(records)
    low, high = wilson_interval(successes, trials) if trials else (None, None)
    failures = Counter(str(row.get("failure_type", "unknown")) for row in records if not row.get("success"))
    by_category: dict[str, dict[str, Any]] = {}
    for category in sorted({str(row.get("category", "uncategorized")) for row in records}):
        subset = [row for row in records if str(row.get("category", "uncategorized")) == category]
        category_successes = sum(bool(row.get("success")) for row in subset)
        category_low, category_high = wilson_interval(category_successes, len(subset)) if subset else (None, None)
        by_category[category] = {"trials": len(subset), "successes": category_successes,
                                 "rate": category_successes / len(subset) if subset else None,
                                 "confidence_interval_95": [category_low, category_high]}
    return {"suite": suite, "trials": trials, "successes": successes,
            "rate": successes / trials if trials else None,
            "confidence_interval_95": [low, high], "failure_taxonomy": dict(sorted(failures.items())),
            "by_category": by_category, "rows": records}
