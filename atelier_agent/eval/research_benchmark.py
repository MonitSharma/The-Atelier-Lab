"""Frozen deep-research benchmark and model-comparison report.

The benchmark deliberately records observable workflow quality rather than
pretending that keyword matching is a complete factual judge. A human or a
later judge can inspect each persisted workflow using its run ID.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from atelier.config import settings
from atelier.service import AtelierService

SUITE_PATH = settings.root.parent / "benchmarks" / "research_deep" / "questions.json"


def load_suite(path: Path = SUITE_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError(f"Invalid research benchmark suite: {path}")
    return payload


def _domain_matches(url: str | None, required: list[str]) -> bool:
    if not required:
        return True
    host = (urlparse(url or "").hostname or "").casefold()
    return any(host == domain or host.endswith(f".{domain}") for domain in required)


def _score_case(case: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    verification = result.get("outputs", {}).get("verify report", {})
    markdown = str(verification.get("report_markdown") or "").casefold()
    expected = [str(item).casefold() for item in case.get("expected_contains", [])]
    matched = [item for item in expected if item in markdown]
    source_rows = verification.get("report_markdown", "").split("## Selected sources", 1)
    source_text = source_rows[1] if len(source_rows) == 2 else ""
    domains = case.get("required_source_domains", [])
    source_domain_hits = sum(1 for domain in domains if domain.casefold() in source_text.casefold())
    return {
        "id": case["id"],
        "status": result.get("status"),
        "run_id": result.get("run_id"),
        "research_complete": bool(verification.get("research_complete")),
        "citation_integrity": bool(verification.get("citation_integrity")),
        "expected_count": len(expected),
        "matched_count": len(matched),
        "matched": matched,
        "required_source_count": len(domains),
        "source_domain_hits": source_domain_hits,
        "quality_pass": bool(verification.get("citation_integrity")) and len(matched) >= max(1, len(expected) // 2),
    }


def run(
    *,
    models: list[str],
    depth: str = "quick",
    suite_path: Path = SUITE_PATH,
    max_web_pages: int = 0,
    model_free: bool = False,
) -> dict[str, Any]:
    suite = load_suite(suite_path)
    service = AtelierService()
    reports: list[dict[str, Any]] = []
    for model in models:
        model_rows: list[dict[str, Any]] = []
        for case in suite["cases"]:
            started = time.monotonic()
            result = service.deep_research(
                case["question"], depth=depth, max_web_pages=max_web_pages,
                max_report_sources=5, model=model, model_free=model_free,
            )
            row = _score_case(case, result)
            row["latency_s"] = round(time.monotonic() - started, 1)
            model_rows.append(row)
        reports.append({
            "model": model,
            "cases": model_rows,
            "aggregate": {
                "cases": len(model_rows),
                "quality_pass": sum(bool(row["quality_pass"]) for row in model_rows),
                "citation_integrity": sum(bool(row["citation_integrity"]) for row in model_rows),
                "research_complete": sum(bool(row["research_complete"]) for row in model_rows),
                "avg_latency_s": round(sum(row["latency_s"] for row in model_rows) / max(1, len(model_rows)), 1),
            },
        })
    return {
        "suite": suite.get("suite", suite_path.stem),
        "created_at": datetime.now(UTC).isoformat(),
        "models": reports,
        "note": "Keyword and citation metrics are screening signals; inspect persisted workflow runs before promotion.",
    }


def save(report: dict[str, Any]) -> Path:
    output_dir = settings.data_dir / "research_benchmark_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = output_dir / f"report_{stamp}.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return path
