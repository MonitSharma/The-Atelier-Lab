"""Scientific retrieval benchmark without calling a reasoning model."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atelier.config import settings
from rag.retrieve import retrieve

QUERIES = [
    ("sample average approximation regret bounds", ["Data-Driven Newsvendor Problem.pdf"]),
    ("quantum CVaR tail risk decision quality", ["tail_risk.pdf", "qshield.pdf"]),
    ("CVaR decision gap quantum estimation error", ["tail_risk.pdf", "qshield.pdf"]),
    ("papers and prior literature on sample average approximation for inventory control", ["Data-Driven Newsvendor Problem.pdf"]),
    ("quantum", ["qshield.pdf", "tail_risk.pdf"]),
]


def evaluate_hits(query: str, hits: list[dict[str, Any]], expected_sources: list[str]) -> dict[str, Any]:
    names = [Path(hit.get("metadata", {}).get("source", "")).name for hit in hits]
    return {
        "query": query,
        "top_sources": names,
        "top_sections": [hit.get("metadata", {}).get("section_type", "other") for hit in hits],
        "expected_sources": expected_sources,
        "hit": any(name in expected_sources for name in names),
        "reference_dominated": bool(names) and sum(
            hit.get("metadata", {}).get("section_type") == "references" for hit in hits[:3]
        ) >= 2,
    }


def run_local_retrieval_benchmark(k: int = 6) -> dict[str, Any]:
    rows = []
    for query, expected in QUERIES:
        rows.append(evaluate_hits(query, retrieve(query, k=k), expected))
    report = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "embedding_model": settings.embed_model,
        "embedding_dimension": settings.embed_dimension,
        "rows": rows,
        "aggregate": {
            "queries": len(rows),
            "hits": sum(row["hit"] for row in rows),
            "reference_dominated_queries": sum(row["reference_dominated"] for row in rows),
        },
    }
    output_dir = settings.data_dir / "eval_reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "retrieval-latest.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["output"] = str(output)
    return report
