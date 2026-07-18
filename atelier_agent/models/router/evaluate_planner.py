"""Measure the planner-router fine-tune: base vs LoRA-adapted on the held-out set.

The planner-router emits a compact JSON *plan* per task (category, difficulty,
edit_scope, tool_plan, model_route), not a single label. So we score it as
structured JSON: parse each prediction, compare it field-by-field to the gold
plan, and report

  - exact_match:   all five fields correct (the strict bar),
  - per-field acc: how often each field is right on its own,
  - route_acc:     model_route correct — the field that actually saves compute.

Runs the 0.5B model twice over ``planner_data/test.jsonl`` — once stock, once
with the trained adapter — so the lift is the evidence the fine-tune taught the
planner something. Kept deliberately separate from ``evaluate.py`` (the binary
difficulty router) because the two adapters answer different questions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_MODEL = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"
ADAPTER = HERE / "planner_adapter"
FIELDS = ["category", "difficulty", "edit_scope", "tool_plan", "model_route"]


def _load_test() -> list[dict]:
    lines = (HERE / "planner_data" / "test.jsonl").read_text().splitlines()
    return [json.loads(ln) for ln in lines if ln.strip()]


def _first_json(text: str) -> dict | None:
    """Extract the first balanced {...} object from model output."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _norm(value) -> str:
    """Canonicalise a field so list order/whitespace differences don't matter."""
    if isinstance(value, list):
        return json.dumps(value, separators=(",", ":"))
    return str(value).strip().lower()


def _score(model, tok, rows: list[dict]) -> dict:
    from mlx_lm import generate

    field_hits = {f: 0 for f in FIELDS}
    exact = 0
    route_hits = 0
    parsed = 0
    for r in rows:
        gold = json.loads(r["completion"])
        out = generate(model, tok, prompt=r["prompt"], max_tokens=96, verbose=False)
        pred = _first_json(out)
        if pred is None:
            continue
        parsed += 1
        all_ok = True
        for f in FIELDS:
            ok = _norm(pred.get(f)) == _norm(gold.get(f))
            field_hits[f] += int(ok)
            all_ok = all_ok and ok
        exact += int(all_ok)
        route_hits += int(_norm(pred.get("model_route")) == _norm(gold.get("model_route")))
    n = len(rows)
    return {
        "n_test": n,
        "parsed_json_rate": round(parsed / n, 3),
        "exact_match": round(exact / n, 3),
        "route_acc": round(route_hits / n, 3),
        "per_field_acc": {f: round(field_hits[f] / n, 3) for f in FIELDS},
    }


def _run(adapter: Path | None) -> dict:
    from mlx_lm import load

    model, tok = load(BASE_MODEL, adapter_path=str(adapter) if adapter else None)
    return _score(model, tok, _load_test())


def main() -> dict:
    base = _run(None)
    has_adapter = ADAPTER.exists() and any(ADAPTER.glob("*.safetensors"))
    tuned = _run(ADAPTER) if has_adapter else None
    result = {
        "base": base,
        "finetuned": tuned,
        "exact_match_lift": round(tuned["exact_match"] - base["exact_match"], 3)
        if tuned
        else None,
        "route_acc_lift": round(tuned["route_acc"] - base["route_acc"], 3)
        if tuned
        else None,
    }
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    main()
