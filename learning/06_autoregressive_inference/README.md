# 06 — Autoregressive inference

**Concept.** Prefill processes the prompt; decode emits one token at a time. Temperature, top-k, top-p, and KV caching change the latency/quality trade-off. **Background.** Softmax and attention. **Shapes.** Cached K/V `(batch, heads, cached_time, head_dim)`.

**Task.** Generate from `minillm` and compare greedy versus sampled output. **Verify.** The local inference experiment records TTFT, prefill, and decode separately. **Mistakes.** Measuring a warm prompt-cache hit as prefill and confusing tokens/sec between phases.

**Production connection.** See `foundation/experiments/003_local_inference_benchmark/`. **Read.** KV-cache and serving notes. **Exit.** Explain why decode is commonly memory-bandwidth-bound.
