# Project vision

The lab studies one connected problem from three angles:

1. **Foundations:** make tokenization, attention, transformers, training, and inference legible from first principles.
2. **Local AI systems:** measure memory, quantization, KV caching, prefill, decoding, serving, and routing on Apple Silicon.
3. **Reliable agents:** test retrieval, tool use, code modification, verification, memory, and escalation with controlled suites.

The constraint is part of the question: a single researcher, a 36 GB unified-memory Mac, local models, no cloud APIs, and reproducible evidence.

The destination is the **Atelier Workbench**: a local-first, model-agnostic AI layer over the Mac's documents, code, research library, and deterministic tools. The user should interact with one workbench through a web UI, the `atelier` CLI, and eventually Finder actions—not with a collection of individual model interfaces. See the [Atelier Workbench plan](ATELIER_WORKBENCH_PLAN.md) for the architecture, model roles, privacy modes, cloud escalation policy, and build order.
