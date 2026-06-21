"""Scoring functions for the eval harness.

Two layers, both fully local:

* **Deterministic** (always on): keyword coverage, retrieval hit@k, and whether
  the answer cites sources. Reproducible, fast, no model — the backbone of a
  trustworthy ruler (PROJECT.md §9: "never change the ruler casually").
* **LLM-as-judge** (opt-in): the worker model grades correctness and
  groundedness when keyword matching is too brittle. Local, free, but
  non-deterministic — so it augments rather than replaces the deterministic score.
"""

from __future__ import annotations

import json
import re
from typing import Any

_CITE_RE = re.compile(r"\[\d+\]")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace(",", "")).strip()


def keyword_score(answer: str, expected_contains: list[str]) -> float:
    """Fraction of expected key phrases present in the answer (0..1)."""
    if not expected_contains:
        return 1.0
    norm = normalize(answer)
    hits = sum(1 for kw in expected_contains if normalize(kw) in norm)
    return hits / len(expected_contains)


def retrieval_hit(retrieved_sources: list[str], expected_source: str | list[str] | None) -> bool:
    """Did the expected source file appear among the retrieved chunks?"""
    if not expected_source:
        return True
    expected = [expected_source] if isinstance(expected_source, str) else expected_source
    return any(exp.lower() in s.lower() for exp in expected for s in retrieved_sources)


def cites_sources(answer: str) -> bool:
    return bool(_CITE_RE.search(answer))


_JUDGE_SYSTEM = """\
You are a strict grader. Given a QUESTION, the CONTEXT passages an assistant was \
given, and its ANSWER, judge two things:
- correct: is the answer factually right given the context? (true/false)
- grounded: is every claim in the answer supported by the context (no outside \
facts, no invention)? (true/false)
Respond with ONLY a JSON object: {"correct": bool, "grounded": bool, "reason": "<short>"}.
"""


def llm_judge(question: str, answer: str, context: str, *, role: str = "worker") -> dict[str, Any]:
    """Local LLM-as-judge. Returns {correct, grounded, reason} (best-effort)."""
    from agent.brain import chat

    user = f"QUESTION:\n{question}\n\nCONTEXT:\n{context}\n\nANSWER:\n{answer}"
    try:
        raw = chat(
            [{"role": "system", "content": _JUDGE_SYSTEM}, {"role": "user", "content": user}],
            role=role,
            json_mode=True,
        )
        data = json.loads(raw)
        return {
            "correct": bool(data.get("correct", False)),
            "grounded": bool(data.get("grounded", False)),
            "reason": str(data.get("reason", ""))[:200],
        }
    except Exception as exc:  # noqa: BLE001
        return {"correct": False, "grounded": False, "reason": f"judge error: {exc}"}


def aggregate(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, float]:
    """Mean of each numeric/bool key across rows (empty -> 0.0)."""
    out: dict[str, float] = {}
    n = len(rows) or 1
    for k in keys:
        out[k] = round(sum(float(r.get(k, 0)) for r in rows) / n, 3)
    return out


def aggregate_by(rows: list[dict[str, Any]], group_key: str, metric_keys: list[str]) -> dict[str, dict[str, float]]:
    """Aggregate numeric metrics for each value of a metadata field."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = row.get(group_key)
        if value is None:
            continue
        groups.setdefault(str(value), []).append(row)
    return {value: aggregate(group_rows, metric_keys) for value, group_rows in sorted(groups.items())}
