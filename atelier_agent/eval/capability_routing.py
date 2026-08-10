"""Frozen, model-free evaluation for capability-first routing."""

from __future__ import annotations

from typing import Any

from agent.capability_router import CapabilityRouter

# Labels are deliberately explicit and reviewable rather than inferred from
# the router's own output. They form the small development set used to catch
# routing regressions before larger model-backed evaluations.
FROZEN_CASES: tuple[dict[str, Any], ...] = (
    {"id": "paper.abstract", "task": "summarize this paper abstract", "domain": "paper", "workflow": "paper_fast", "abstain": False},
    {"id": "paper.deep", "task": "deep read the methodology and results section of this PDF", "domain": "paper", "workflow": "paper_deep_read", "abstain": False},
    {"id": "code.fix", "task": "fix the failing tests in this repository", "domain": "code", "workflow": "code_fix", "abstain": False},
    {"id": "code.refactor", "task": "refactor this Python function and run regression tests", "domain": "code", "workflow": "code_fix", "abstain": False},
    {"id": "data.csv", "task": "profile this CSV and report missing values", "domain": "data", "workflow": "data_analyze", "abstain": False},
    {"id": "data.sqlite", "task": "inspect this SQLite database schema", "domain": "data", "workflow": "data_analyze", "abstain": False},
    {"id": "vision.figure", "task": "explain the scientific figure in this PDF", "domain": "vision", "workflow": "figure_inspect", "abstain": False},
    {"id": "vision.scan", "task": "OCR this scanned equation image", "domain": "vision", "workflow": "figure_inspect", "abstain": False},
    {"id": "research.local", "task": "verify this citation against the local paper", "domain": "research", "workflow": "research_verify", "abstain": False},
    {"id": "research.web-denied", "task": "search the web for the latest DOI", "domain": "research", "workflow": "research_verify", "abstain": True},
    {"id": "quantum.qasm", "task": "simulate this Qiskit circuit", "domain": "quantum", "workflow": "quantum_analyze", "abstain": False},
    {"id": "quantum.backend", "task": "compare quantum backends for this circuit", "domain": "quantum", "workflow": "quantum_analyze", "abstain": False},
    {"id": "optimization.lp", "task": "solve this linear program with constraints", "domain": "optimization", "workflow": "optimization_validate", "abstain": False},
    {"id": "optimization.qubo", "task": "validate this QUBO solution", "domain": "optimization", "workflow": "optimization_validate", "abstain": False},
    {"id": "general.notes", "task": "remember this project decision", "domain": "general", "workflow": "general", "abstain": False},
    {"id": "general.math", "task": "calculate 47 times 89", "domain": "general", "workflow": "general", "abstain": False},
)


def run_capability_eval() -> dict[str, Any]:
    router = CapabilityRouter(backend="heuristic")
    rows: list[dict[str, Any]] = []
    for case in FROZEN_CASES:
        decision = router.decide(case["task"])
        row = {
            "id": case["id"],
            "task": case["task"],
            "expected": {key: case[key] for key in ("domain", "workflow", "abstain")},
            "actual": {"domain": decision.domain, "workflow": decision.workflow, "abstain": decision.abstain},
        }
        row["domain_correct"] = decision.domain == case["domain"]
        row["workflow_correct"] = decision.workflow == case["workflow"]
        row["abstention_correct"] = decision.abstain == case["abstain"]
        row["success"] = all(row[key] for key in ("domain_correct", "workflow_correct", "abstention_correct"))
        rows.append(row)
    total = len(rows)
    return {
        "schema_version": 1,
        "suite": "capability_routing_frozen",
        "backend": "heuristic",
        "cases": total,
        "successes": sum(row["success"] for row in rows),
        "domain_accuracy": sum(row["domain_correct"] for row in rows) / total,
        "workflow_accuracy": sum(row["workflow_correct"] for row in rows) / total,
        "abstention_accuracy": sum(row["abstention_correct"] for row in rows) / total,
        "rows": rows,
    }
