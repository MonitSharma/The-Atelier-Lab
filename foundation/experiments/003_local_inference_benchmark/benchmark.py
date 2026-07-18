"""Local LLM inference benchmark for Apple Silicon (Ollama backend).

Measures the two phases of transformer inference separately, because they have
different bottlenecks and matter for different reasons:

  * PREFILL  — processing the prompt. Compute-bound, parallel over prompt
    tokens. Dominates time-to-first-token (TTFT). Scales with prompt length.
  * DECODE   — generating tokens one at a time. Memory-bandwidth-bound (must
    stream the whole model + KV cache per token). Sets steady-state tokens/sec
    and is what a user "feels" while text streams.

Ollama returns authoritative per-request timings (nanoseconds), so we read
those rather than guessing from wall-clock:

  load_duration        model load (cold start only)
  prompt_eval_count    prompt tokens processed (prefill)
  prompt_eval_duration prefill time
  eval_count           tokens generated (decode)
  eval_duration        decode time

Derived metrics:
  decode_tok_s   = eval_count        / eval_duration
  prefill_tok_s  = prompt_eval_count / prompt_eval_duration
  ttft_ms (warm) = prompt_eval_duration   (model already resident)

Each (model, prompt-length) cell is warmed once, then measured REPEATS times.
Resident memory is read from /api/ps after generation.

Usage:
  python benchmark.py                       # qwen3:4b, qwen3:14b
  python benchmark.py --models qwen3:4b gemma4:26b
  python benchmark.py --repeats 5 --num-predict 256
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

HOST = "http://localhost:11434"
HERE = Path(__file__).resolve().parent
NS = 1e9  # nanoseconds per second

# Two prompt lengths to expose prefill scaling. The long prompt is built by
# repeating a paragraph so the token count is comfortably larger.
SHORT_PROMPT = "Explain what a KV cache is in one sentence."
_PARA = (
    "The transformer processes a prompt in a prefill phase and then generates "
    "tokens one at a time in a decode phase. Prefill is compute-bound while "
    "decode is memory-bandwidth-bound. "
)
LONG_PROMPT = (_PARA * 40) + "\nNow summarize the paragraph above in one sentence."


def _post(path: str, payload: dict, timeout: float = 600.0) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        HOST + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _generate(model: str, prompt: str, num_predict: int) -> dict:
    """One non-streaming generation; returns Ollama's timing block."""
    return _post(
        "/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict, "temperature": 0, "seed": 0},
        },
    )


def _resident_memory_bytes(model: str) -> dict:
    """Read model footprint from /api/ps (total + how much is on the GPU)."""
    try:
        with urllib.request.urlopen(HOST + "/api/ps", timeout=30) as r:
            ps = json.loads(r.read().decode())
    except Exception:
        return {}
    for m in ps.get("models", []):
        if m.get("name") == model or m.get("model") == model:
            return {"size_bytes": m.get("size"), "size_vram_bytes": m.get("size_vram")}
    return {}


def _metrics(r: dict) -> dict:
    ec, ed = r.get("eval_count", 0), r.get("eval_duration", 0)
    pc, pd = r.get("prompt_eval_count", 0), r.get("prompt_eval_duration", 0)
    return {
        "prompt_tokens": pc,
        "gen_tokens": ec,
        "decode_tok_s": (ec / (ed / NS)) if ed else None,
        "prefill_tok_s": (pc / (pd / NS)) if pd else None,
        "ttft_ms": (pd / 1e6) if pd else None,  # warm TTFT ~ prefill time
        "load_ms": (r.get("load_duration", 0) / 1e6),
        "total_ms": (r.get("total_duration", 0) / 1e6),
    }


def bench_cell(model: str, prompt: str, label: str, num_predict: int, repeats: int) -> dict:
    # Warm up the MODEL (pay the one-time weight load) with a throwaway prompt.
    # We must NOT warm up with `prompt` itself: Ollama caches the prompt KV, so a
    # second identical send skips prefill (measured here: 818ms -> 26ms) and would
    # inflate prefill_tok_s and understate TTFT. Each measured run therefore gets
    # a unique nonce prefix to force a real cache-missing prefill every time.
    _generate(model, "warmup " + uuid.uuid4().hex, num_predict)
    runs = [
        _metrics(_generate(model, f"[{uuid.uuid4().hex}] {prompt}", num_predict))
        for _ in range(repeats)
    ]

    def agg(key: str) -> float | None:
        vals = [x[key] for x in runs if x[key] is not None]
        return round(statistics.mean(vals), 2) if vals else None

    return {
        "prompt_len": label,
        "prompt_tokens": runs[0]["prompt_tokens"],
        "decode_tok_s": agg("decode_tok_s"),
        "prefill_tok_s": agg("prefill_tok_s"),
        "ttft_ms": agg("ttft_ms"),
        "repeats": repeats,
        **_resident_memory_bytes(model),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen3:4b", "qwen3:14b"])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--num-predict", type=int, default=128)
    args = ap.parse_args()

    conditions = [("short", SHORT_PROMPT), ("long", LONG_PROMPT)]
    report: dict = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": "Apple M3 Pro / 36GB / macOS",
        "backend": "ollama",
        "num_predict": args.num_predict,
        "repeats": args.repeats,
        "results": [],
    }

    for model in args.models:
        for label, prompt in conditions:
            print(f"  benchmarking {model:14s} [{label} prompt] ...", flush=True)
            t0 = time.time()
            cell = bench_cell(model, prompt, label, args.num_predict, args.repeats)
            cell["model"] = model
            cell["wall_s"] = round(time.time() - t0, 1)
            report["results"].append(cell)

    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    out = HERE / "results" / f"bench_{stamp}.json"
    out.write_text(json.dumps(report, indent=2))

    # Console summary table.
    print(f"\nSaved {out}\n")
    hdr = f"{'model':14s} {'prompt':7s} {'ptoks':>6s} {'decode t/s':>11s} {'prefill t/s':>12s} {'TTFT ms':>9s} {'mem GB':>7s}"
    print(hdr)
    print("-" * len(hdr))
    for c in report["results"]:
        mem = c.get("size_bytes")
        mem_gb = f"{mem / 1e9:.1f}" if mem else "-"
        print(
            f"{c['model']:14s} {c['prompt_len']:7s} {c['prompt_tokens']:>6d} "
            f"{c['decode_tok_s'] or 0:>11.1f} {c['prefill_tok_s'] or 0:>12.1f} "
            f"{c['ttft_ms'] or 0:>9.1f} {mem_gb:>7s}"
        )


if __name__ == "__main__":
    main()
