"""Quantization sweep: accuracy vs speed vs memory for one model at 4/8/16-bit.

Experiment 003 (benchmark.py) measured *speed* across model sizes. This measures
the other axis of the deployment trade-off: what does precision cost and buy for
a *fixed* model? We hold the model constant (qwen3 4B) and vary only the
quantization (Q4_K_M -> Q8_0 -> FP16), then measure three things per variant:

  1. accuracy  — a fixed deterministic task set (same prompts, temperature 0),
                 scored by normalized substring match. Relative accuracy across
                 variants is the signal (same ruler for all).
  2. decode t/s — steady-state generation speed (Ollama eval timings).
  3. memory     — resident footprint from /api/ps.

qwen3 emits <think>...</think> by default; we append "/no_think" so the probe
scores direct answers cleanly and quickly. Each timed/probed prompt gets a nonce
prefix to defeat Ollama's prompt cache (see benchmark.py's methodology note).

Usage:
  python quant_sweep.py                       # default q4/q8/fp16 of qwen3:4b
  python quant_sweep.py --models qwen3:4b qwen3:4b-q8_0 qwen3:4b-fp16
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
import urllib.request
import uuid
from datetime import UTC, datetime
from pathlib import Path

HOST = "http://localhost:11434"
HERE = Path(__file__).resolve().parent
NS = 1e9

# (tag, human label). The default qwen3:4b is Q4_K_M (confirmed via `ollama show`).
DEFAULT_MODELS = [
    ("qwen3:4b", "Q4_K_M"),
    ("qwen3:4b-q8_0", "Q8_0"),
    ("qwen3:4b-fp16", "FP16"),
]

# Deterministic probes: (prompt, expected normalized substring). Mixed difficulty
# so the set can discriminate degradation without a total floor/ceiling effect.
TASKS: list[tuple[str, str]] = [
    ("What is the capital of France? Answer with only the city name.", "paris"),
    ("What is the chemical symbol for gold? Answer with only the symbol.", "au"),
    ("Compute 47 * 89. Give only the number.", "4183"),
    ("Compute 128 + 256. Give only the number.", "384"),
    ("What is 15% of 200? Give only the number.", "30"),
    ("Compute 1024 / 8. Give only the number.", "128"),
    ("What is the square root of 144? Give only the number.", "12"),
    ("What comes next: 2, 4, 8, 16, ? Give only the number.", "32"),
    ("Is 17 a prime number? Answer yes or no.", "yes"),
    ("How many days are in a leap year? Give only the number.", "366"),
    ("Reverse the word 'python'. Give only the reversed word.", "nohtyp"),
    ("What is the past tense of 'go'? Give only one word.", "went"),
    ("Translate 'hello' into Spanish. Give only one word.", "hola"),
    ("What planet is known as the Red Planet? One word.", "mars"),
    ("Sort ascending: 3 1 2. Give them space-separated.", "1 2 3"),
    ("The opposite of 'hot' is ___. Give only one word.", "cold"),
]

TIMED_PROMPT = "Write three sentences about why local AI matters."


def _gen(model: str, prompt: str, num_predict: int) -> dict:
    body = json.dumps(
        {
            "model": model,
            "prompt": f"[{uuid.uuid4().hex}] {prompt} /no_think",
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0, "seed": 0},
        }
    ).encode()
    req = urllib.request.Request(
        HOST + "/api/generate", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


def _norm(text: str) -> str:
    """Lowercase, drop <think> blocks, strip commas so 4,183 == 4183."""
    text = re.sub(r"<think>.*?</think>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    return re.sub(r",", "", text.lower())


def _memory_gb(model: str) -> float | None:
    try:
        with urllib.request.urlopen(HOST + "/api/ps", timeout=30) as r:
            ps = json.loads(r.read().decode())
    except Exception:
        return None
    for m in ps.get("models", []):
        if m.get("name") == model or m.get("model") == model:
            return round((m.get("size") or 0) / 1e9, 1)
    return None


def _decode_tok_s(model: str, repeats: int = 3) -> float:
    _gen(model, TIMED_PROMPT, 64)  # warmup / load
    rates = []
    for _ in range(repeats):
        r = _gen(model, TIMED_PROMPT, 128)
        ec, ed = r.get("eval_count", 0), r.get("eval_duration", 0)
        if ed:
            rates.append(ec / (ed / NS))
    return round(statistics.mean(rates), 1) if rates else 0.0


def _accuracy(model: str) -> tuple[float, list[dict]]:
    hits, detail = 0, []
    for prompt, expected in TASKS:
        out = _gen(model, prompt, 64).get("response", "")
        ok = expected in _norm(out)
        hits += int(ok)
        detail.append({"expected": expected, "ok": ok})
    return round(hits / len(TASKS), 3), detail


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--models",
        nargs="+",
        default=[t for t, _ in DEFAULT_MODELS],
        help="Ollama tags to sweep (quant variants of the same base model).",
    )
    args = ap.parse_args()
    labels = dict(DEFAULT_MODELS)

    report = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": "Apple M3 Pro / 36GB / macOS",
        "base_model": "qwen3:4b",
        "n_tasks": len(TASKS),
        "results": [],
    }
    for tag in args.models:
        print(f"  sweeping {tag} ...", flush=True)
        t0 = time.time()
        mem = _memory_gb(tag) or _memory_gb(tag)  # after warmup it's resident
        tok_s = _decode_tok_s(tag)
        mem = _memory_gb(tag)
        acc, detail = _accuracy(tag)
        report["results"].append(
            {
                "tag": tag,
                "quant": labels.get(tag, "?"),
                "accuracy": acc,
                "decode_tok_s": tok_s,
                "memory_gb": mem,
                "wall_s": round(time.time() - t0, 1),
                "detail": detail,
            }
        )

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = HERE / "results" / f"quant_sweep_{stamp}.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nSaved {out}\n")

    hdr = f"{'quant':8s} {'tag':16s} {'accuracy':>9s} {'decode t/s':>11s} {'mem GB':>7s}"
    print(hdr)
    print("-" * len(hdr))
    for c in report["results"]:
        acc_pct = f"{c['accuracy'] * 100:.0f}% ({int(c['accuracy'] * report['n_tasks'])}/{report['n_tasks']})"
        print(
            f"{c['quant']:8s} {c['tag']:16s} {acc_pct:>9s} "
            f"{c['decode_tok_s']:>11.1f} {str(c['memory_gb']):>7s}"
        )


if __name__ == "__main__":
    main()
