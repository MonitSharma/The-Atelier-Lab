"""Measure the routing win on a real workload (the doc-QA suite).

For each question we: classify it with the router, answer it with the worker
(4B) and with the brain (14B), and score both. From this we report:
  * how many questions route to the cheap model (brain calls saved);
  * whether routed answers stay correct vs. always-brain (does routing hurt?).

This is the concrete Phase 6 claim, measured rather than assumed.
"""

from __future__ import annotations

import json

from atelier.config import settings
from eval import metrics

DOCQA_FILE = settings.root / "eval" / "tasks_docqa" / "tasks.json"


def run() -> dict:
    from agent.router import Router
    from rag.answer import answer_question

    router = Router()  # auto: fine-tuned if trained
    tasks = json.loads(DOCQA_FILE.read_text())["tasks"]

    rows = []
    for t in tasks:
        q, expect = t["question"], t.get("expected_contains", [])
        difficulty = router.classify(q)
        worker = answer_question(q, role="worker")
        brain = answer_question(q, role="brain")
        rows.append({
            "id": t["id"],
            "difficulty": difficulty,
            "worker_correct": int(metrics.keyword_score(worker.text, expect) >= 0.5),
            "brain_correct": int(metrics.keyword_score(brain.text, expect) >= 0.5),
        })

    n = len(rows)
    n_easy = sum(1 for r in rows if r["difficulty"] == "easy")
    # Routed = worker on easy, brain on hard.
    routed_correct = sum(
        r["worker_correct"] if r["difficulty"] == "easy" else r["brain_correct"]
        for r in rows
    )
    brain_correct = sum(r["brain_correct"] for r in rows)

    result = {
        "router_backend": router.name,
        "n": n,
        "routed_to_worker": n_easy,
        "brain_calls_saved_pct": round(100 * n_easy / n, 1),
        "routed_accuracy": round(routed_correct / n, 3),
        "always_brain_accuracy": round(brain_correct / n, 3),
        "rows": rows,
    }
    print(json.dumps(result, indent=2))
    out = settings.data_dir / "eval_reports" / "route_eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
