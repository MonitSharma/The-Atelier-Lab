# Experiment 003: Local Inference Benchmark (Apple M3 Pro)

**Question:** What is the real inference cost of the local models Atelier depends
on — and where does the time actually go? This is the deployment/serving
counterpart to Experiment 000 (which measured *training* throughput).

The point is not just to get tokens/sec numbers, but to measure the **two phases
of transformer inference separately**, because they have different bottlenecks
and matter for different reasons.

---

## Background: prefill vs decode

Every generation request has two phases:

| Phase | What it does | Bottleneck | What it sets |
| :--- | :--- | :--- | :--- |
| **Prefill** | Process the whole prompt at once, fill the KV cache | **Compute** (parallel over prompt tokens) | Time-to-first-token (TTFT) |
| **Decode** | Generate output tokens one at a time | **Memory bandwidth** (stream the model + KV cache *per token*) | Steady-state tokens/sec |

Decode is memory-bandwidth-bound because generating each token requires reading
every model weight from memory once. That is why a bigger model is slower to
decode almost in proportion to its size — you are moving more bytes per token,
not doing more useful math per token.

Ollama returns authoritative per-request timings (`prompt_eval_*` = prefill,
`eval_*` = decode), so [`benchmark.py`](benchmark.py) reads those rather than
guessing from wall-clock.

---

## Results

`python benchmark.py --models qwen3:4b qwen3:14b gemma4:26b` — Ollama, all
Q4_K_M, 3 repeats, 128 tokens generated, short (~52-token) and long (~1500-token)
prompts.

| Model | Params | Prompt | Decode tok/s | Prefill tok/s | TTFT (ms) | Resident mem |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: |
| **qwen3:4b** | 4B | short | **39.3** | 453.4 | 114 | 7.5 GB |
| **qwen3:4b** | 4B | long | 37.4 | 591.0 | 2523 | 7.5 GB |
| **qwen3:14b** | 14.8B | short | **11.5** | 127.3 | 382 | 14.4 GB |
| **qwen3:14b** | 14.8B | long | 11.3 | 153.3 | 9885 | 14.4 GB |
| **gemma4:26b** | 25.8B | short | **27.9** | 140.3 | 401 | 17.4 GB |
| **gemma4:26b** | 25.8B | long | 27.9 | 362.1 | 4377 | 17.4 GB |

Raw reports are in [`results/`](results/).

### What the numbers say

1. **Within one model family, decode is memory-bound and it shows.** The 14B
   Qwen has ~4× the parameters of the 4B, uses ~2× the memory, and decodes
   ~**3.4×slower** (11.5 vs 39.3 tok/s). Decode throughput barely moves between
   short and long prompts — for a fixed model it depends on how many bytes must
   be streamed per token, not on prompt length.

2. **Across families, parameter count alone does NOT predict decode speed.**
   The headline surprise: **gemma4:26b (25.8B, 17.4 GB) decodes 2.5× *faster*
   than qwen3:14b (14.8B, 14.4 GB)** — a bigger model that is quicker per token,
   at the *same* Q4_K_M quantization. A naive "more params = slower decode"
   model is wrong. What actually sets per-token cost is bytes-moved-per-token,
   which depends on architecture *shape*, not just total size: gemma runs a much
   narrower hidden dimension (2816 vs Qwen's 5120) and a different attention/KV
   configuration, and the llama.cpp Metal kernels evidently execute that shape
   more efficiently. (Confirming the exact split — KV-head/GQA ratio vs kernel
   efficiency — would need the GGUF head-count metadata and a profiler; the
   measurement stands regardless.) **Lesson: benchmark the model you will
   actually serve; don't extrapolate latency from parameter count.**

3. **Prefill is ~11× cheaper per token than decode** (4B: 453 vs 39 tok/s),
   because prefill processes all prompt tokens in parallel while decode is
   strictly sequential. Prefill throughput is roughly constant across prompt
   lengths, as expected for a compute-bound phase.

4. **TTFT is a prompt-length tax, not a model-speed tax.** A ~1,500-token prompt
   costs **2.5 s** to first token on the 4B and **9.9 s** on the 14B — before a
   single output token appears. (Note gemma's lower 4.4 s TTFT on the long
   prompt, tracking its faster per-token rate.) For an interactive agent, long
   contexts are expensive at the *front* of the response, which is exactly what
   prompt/prefix caching (below) exists to avoid.

5. **Routing to the worker is quantifiably cheaper.** The 4B worker decodes
   ~3.4× faster and uses half the memory of the 14B brain. This is the concrete
   latency/memory payoff behind Atelier's easy→worker, hard→brain routing
   policy — the router work and this benchmark measure two halves of the same
   trade-off. (And per point 2, the "heavy" 26B is *not* the slowest option —
   another reason to measure rather than assume.)

---

## Methodology note: the prompt-caching trap (and the fix)

The first run reported a **prefill throughput of 52,000 tok/s** for the 4B on the
long prompt — physically impossible on this hardware (~90× the short-prompt
prefill). That was a measurement bug, and finding it is half the value of the
experiment.

**Cause:** the harness warmed up each cell by sending the *same* prompt it then
measured. Ollama caches the prompt's KV state, so the second identical send skips
prefill entirely. Probed directly:

```
1st send (cold prefill):     ptoks=455  prefill=818.7 ms
2nd send (identical -> cache): ptoks=455  prefill= 25.8 ms   # 32x faster, skipped
3rd send (nonce prefix):     ptoks=460  prefill=775.6 ms   # cache miss, real again
```

**Fix:** warm up the *model* (pay the one-time weight load) with a throwaway
prompt, then give every measured run a unique nonce prefix so prefill actually
runs each time. The corrected prefill numbers (447–579 tok/s) are internally
consistent — TTFT now scales linearly with prompt length, as a real prefill must.

**The deeper lesson:** that 32× speedup *is* a real deployment lever. Prompt /
prefix caching (Ollama here, PagedAttention/automatic-prefix-caching in vLLM) is
how production systems avoid re-paying prefill for shared prompt prefixes — e.g.
a fixed system prompt reused across every request. The benchmark accidentally
demonstrated the exact optimization it first mismeasured.

---

## Reproduce

```bash
# Ollama must be serving (ollama serve). Models: qwen3:4b, qwen3:14b pulled.
cd foundation/experiments/003_local_inference_benchmark
python benchmark.py                          # default: 4b + 14b
python benchmark.py --models qwen3:4b gemma4:26b --repeats 5 --num-predict 256
```

## Terms this experiment makes concrete

KV cache · prefill vs decode · time-to-first-token (TTFT) · memory-bandwidth-bound
· tokens/sec · quantization (4-bit) · prompt / prefix caching · resident model
footprint · latency vs throughput.
