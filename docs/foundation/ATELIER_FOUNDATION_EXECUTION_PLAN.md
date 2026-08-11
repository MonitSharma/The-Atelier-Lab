# Atelier Foundation — Learning and Execution Plan

**Start date:** 13 August 2026  
**Branch:** `atelier-foundation`  
**Primary hardware:** MacBook Pro, M3 Pro, 36 GB unified memory  
**Expected cadence:** 10–15 focused hours per week  
**Research horizon:** approximately 12–16 weeks before the first meaningful sparse-model result

This plan translates the [Local Sparse Language Model Research Plan](LOCAL_SPARSE_LANGUAGE_MODEL_RESEARCH_PLAN.md) into a practical learning sequence. The objective is to understand and implement every important component personally, establish a trustworthy dense baseline, and only then investigate sparse conditional computation.

## North star

The project asks:

> Can a four-expert, top-1 sparse language model use a cheap signal derived from residual dynamics to improve language-modeling quality at matched active compute, while remaining practical on Apple Silicon?

The central comparison is:

```text
Atelier-D50
    vs
Atelier-D133
    vs
Atelier-M133 (standard router)
    vs
Atelier-M133-S (stability-aware router)
```

The first objective is not to build the MoE. The first objective is to earn a dense baseline whose correctness, data, training history, speed, and failures are understood.

## Non-negotiable working rules

1. Write the implementation personally. Use reviews and explanations to improve it, but do not paste large generated implementations without understanding each operation.
2. Introduce one concept at a time and test it before composing it into a larger component.
3. Every tensor transformation must have a documented shape.
4. Every full training run must be reproducible from a committed configuration and an external data manifest.
5. Datasets, checkpoints, tokenized shards, caches, and large logs stay outside Git.
6. Benchmark runs must fail on unsupported MPS operations rather than silently falling back to the CPU.
7. Do not compare models that received different data, token order, tuning effort, or decoding settings.
8. Do not scale a model while a smaller version still has unexplained behavior.
9. Negative results are recorded, not hidden.
10. Novelty claims remain provisional until checked against current primary literature.

## Teacher–builder workflow

For each component:

1. Read the relevant mathematics and describe the component in plain language.
2. Write down its input and output shapes before coding.
3. Implement the smallest correct form.
4. Write a focused test.
5. Compare CPU and MPS behavior where applicable.
6. Review the implementation for correctness, clarity, numerical stability, and Apple-specific performance.
7. Record what was learned and commit the completed unit.

A productive two-to-three-hour session should usually contain:

- 20–30 minutes of reading or derivation
- 60–90 minutes of implementation
- 30–45 minutes of tests and debugging
- 15 minutes of notes and a small commit

## Model ladder

| Model | Role | Approximate size | When it is allowed |
|---|---|---:|---|
| Micro model | Unit tests and exact inspection | under 1M | Immediately |
| Atelier-D20 | Pipeline and overfit model | 18.7M | After component tests pass |
| Atelier-D50 | First serious dense baseline | 48.5M | After D20 trains and resumes reliably |
| Atelier-D133 | Total-parameter dense control | 133.4M | After D50 baseline is frozen |
| Atelier-M133 | Standard sparse control | 133.4M total / 48.5M active | After MoE correctness and dispatch gates pass |
| Atelier-M133-S | Stability-aware sparse model | same as M133 | After the residual signal independently predicts difficulty |
| Atelier-M162/M251 | Confirmatory scale | 162M/251M total | Only after a smaller result survives repeated seeds |

## Phase 0 — Orient and freeze the scientific contract

**Target:** 13–15 August 2026

### Learn

- Why autoregressive language modeling predicts the next token.
- How cross-entropy relates to negative log likelihood.
- Why BPB is useful when tokenizers differ.
- The difference between total parameters, active parameters, FLOPs, memory, and wall-clock time.
- Why MoE is conditional computation rather than automatic acceleration.

### Do

- Read the executive recommendation, fair-comparison section, architecture proposal, and hard exit criteria in the research plan.
- Inspect the existing `foundation/minillm` implementation without changing it.
- Draw the complete dense forward path on paper.
- Produce a tensor-shape table for embeddings, attention, GQA, SwiGLU, logits, and loss.
- Derive the parameter count of Atelier-D20 and Atelier-D50 by hand.
- Decide the canonical model API and tensor layout: `[batch, sequence, hidden]`.
- Define the first fixed metrics: training CE, validation CE, BPB, tokens/second, step-time quantiles, tensor memory, and driver memory.

### Exit gate

Do not begin the model implementation until you can explain:

- why the causal mask is required;
- why the targets are shifted by one token;
- what each attention dimension means;
- why GQA changes K/V projections but not Q projections;
- why SwiGLU has three learned projections;
- why tied embeddings save parameters;
- why validation data must be split by document rather than arbitrary token positions.

## Phase 1 — Build and test dense-model primitives

**Target:** Week 1–2

Implement in this learning order:

1. Model configuration and parameter-count calculation.
2. RMSNorm.
3. Rotary position embeddings.
4. Causal scaled dot-product attention.
5. Grouped-query attention.
6. SwiGLU feed-forward network.
7. Pre-normalized residual block.
8. Token embeddings and tied output projection.
9. Full decoder model.
10. Autoregressive loss.

For every component, test:

- output shape;
- dtype and device preservation;
- deterministic behavior where expected;
- finite outputs and gradients;
- invalid configuration handling;
- CPU/MPS numerical agreement within an appropriate tolerance.

### Exit gate

- The micro model completes forward and backward passes on CPU and MPS.
- No tensor silently moves devices.
- Causal masking prevents access to future tokens.
- Parameter count matches the hand calculation.
- Save/load reproduces logits exactly in FP32.

## Phase 2 — Implement the training substrate

**Target:** Week 2–3

### Build

- deterministic seeding;
- token-batch loader;
- train/validation split handling;
- AdamW configuration;
- warmup plus cosine learning-rate schedule;
- gradient clipping;
- gradient accumulation;
- checkpoint save and resume;
- lightweight metric collection;
- MPS memory logging;
- generation for qualitative inspection.

### Required tests

- Interrupted and resumed training produces the expected next-step loss.
- Gradient accumulation matches an equivalent larger batch within tolerance.
- Validation does not update parameters or optimizer state.
- The scheduler resumes at the correct step.
- Checkpoints contain model, optimizer, scheduler, RNG, token count, and configuration state.

### Exit gate

Atelier-D20 must overfit 1–4 fixed sequences, ideally reaching cross-entropy below approximately `0.05` when complete memorization is possible.

## Phase 3 — Validate the end-to-end pipeline

**Target:** Week 3–4

Use a small development corpus, potentially TinyStories, solely to validate the pipeline.

### Do

- Train the tokenizer on the training split only.
- Create document-level train, validation, and test splits.
- Tokenize and shard data outside Git.
- Train D20 on approximately 10–50M tokens.
- Generate fixed samples from fixed prompts at fixed checkpoints.
- Confirm memory does not drift during several thousand steps.
- Confirm loss decreases and validation initially improves.

### Exit gate

- Training is stable.
- Resume works in a real run.
- Throughput is consistent after warmup.
- Generated output changes from noise into recognizable structure.
- Dataset and tokenizer hashes are recorded.

## Phase 4 — Freeze the tokenizer and data protocol

**Target:** Week 4–5

Compare 16k, 24k, and optionally 32k BPE tokenizers on the same source bytes.

Measure:

- bytes per token;
- BPB;
- vocabulary utilization;
- unknown/fallback behavior;
- sequence-length distribution;
- embedding/output-projection parameter cost;
- training throughput.

Use a fixed, documented general-English corpus subset for the first serious model. Prefer one source and one frozen snapshot over a complicated mixture.

### Exit gate

- One tokenizer is selected and frozen.
- The training, validation, and test manifests are immutable.
- Corpus licensing and provenance are recorded.
- The exact token order can be reproduced from a seed and manifest.

## Phase 5 — Establish Atelier-D50

**Target:** Week 5–7

Configuration target:

- 12 layers
- width 512
- 8 query heads
- 2 key/value heads
- head dimension 64
- SwiGLU hidden size 1536
- context length 1024
- approximately 24k vocabulary
- approximately 48.5M parameters

### Run sequence

1. A 1M-token smoke run.
2. A 10M-token integration run.
3. A 50M-token learning-rate pilot.
4. A controlled 100M-token run.
5. The first 500M-token baseline.
6. Extend toward 1B tokens only if the curve and system justify it.

### Record

- loss and BPB curves;
- tokens/second and wall-clock time;
- p50/p95 step time;
- peak tensor and driver memory;
- gradient norms;
- activation norms by depth;
- fixed-prompt samples;
- repeated 3-gram and 4-gram rates;
- distinct-1/2/3 under fixed decoding.

### Exit gate

- No unexplained spikes, NaNs, or memory growth.
- Checkpoint resume is trustworthy.
- Throughput is within 15% of the locally calibrated expectation or the difference is explained.
- The final D50 configuration and training recipe are frozen.
- D50 results are reproducible from a fresh process.

## Phase 6 — Run dense architecture ablations

**Target:** Week 7–8

Run one-variable comparisons at an affordable token budget:

1. LayerNorm versus RMSNorm.
2. GELU versus SwiGLU.
3. Learned positional embeddings versus RoPE.
4. MHA versus GQA.
5. FP32 versus a validated lower-precision path.

Retain a change only when it provides repeatable quality, performance, memory, or simplicity benefits. Freeze the final dense architecture before adding sparsity.

## Phase 7 — Learn and implement MoE correctness

**Target:** Week 8–10

Start on micro models and D20-scale models.

### Learn

- router logits and probabilities;
- top-1 selection;
- straight-through gradient behavior through selected routes;
- Switch-style load balancing;
- router z-loss or equivalent stabilization;
- expert capacity and token dropping;
- expert collapse;
- routing entropy;
- packed versus padded dispatch.

### Implement

- four equal-width FFN experts;
- a simple linear router;
- top-1 selection;
- no token dropping;
- packed dispatch using token sorting;
- inverse permutation;
- per-layer router metrics.

### Correctness gates

- One expert exactly matches the corresponding dense FFN.
- Forced routing to expert `j` matches calling expert `j` directly.
- Dispatch followed by inverse permutation restores exact token order.
- Only routed expert paths receive token gradients.
- No expert remains permanently dead.
- Every token produces one output.
- Comparable active work reaches at least 60–70% of D50 throughput before scaling.

If sparse dispatch is too slow, compare dynamic packed, fixed padded, and bucketed padded layouts before changing the research hypothesis.

## Phase 8 — Establish the matched dense–sparse triangle

**Target:** Week 10–12

Train:

- D50: approximately 48.5M total and active parameters;
- D133: approximately 133.4M total and active parameters;
- M133: approximately 133.4M total and 48.5M active parameters.

Keep identical:

- tokenizer;
- data snapshot;
- token order;
- context length;
- global batch in tokens;
- optimizer family;
- tuning budget;
- training-token budget;
- evaluation prompts and decoding;
- hardware and software environment.

Report both matched-token and matched-active-FLOP views. Active parameter count alone is not a complete compute measurement because attention, routing, and vocabulary projection remain dense.

### Exit gate

Establish whether ordinary sparse capacity helps at this scale and quantify its real MPS throughput penalty. If standard M133 is worse in both quality and wall-clock cost, stop and understand why before introducing a more complex router.

## Phase 9 — Validate the physics-derived signal

**Target:** Week 12–13

Before using residual dynamics for routing, test whether the proposed signal predicts difficulty independently.

Candidate signal:

```text
relative residual update = norm(delta_h) / (norm(h) + epsilon)
```

Measure its relationship to next-token loss while controlling for:

- token frequency;
- sequence position;
- token length;
- punctuation and numeric tokens;
- current router entropy;
- layer depth;
- activation scale.

### Exit gate

The signal must carry independent predictive information about token difficulty. If it does not, reject or revise the hypothesis rather than embedding it into the router.

## Phase 10 — Train the stability-aware router

**Target:** Week 13–15

Compare:

- D50;
- D133;
- standard M133;
- M133-S with the residual-derived router coordinate.

Use at least two seeds at an affordable budget before any large confirmatory run.

Required evidence:

- consistent BPB direction across seeds;
- no expert collapse;
- no increase in active expert count;
- negligible extra active FLOPs;
- useful route changes for high-difficulty tokens;
- repetition improvement under identical decoding;
- tolerable wall-clock overhead on MPS.

## Phase 11 — Apple-specific optimization and MLX comparison

**Target:** Week 15–16 and later

Only optimize after profiling identifies a real bottleneck.

Investigate:

- fewer synchronization points;
- contiguous expert weights;
- larger, regular expert GEMMs;
- fixed or bucketed capacity buffers;
- native scaled dot-product attention;
- precision changes with long-run numerical checks;
- PyTorch profiler and Metal Instruments;
- an MLX backend or isolated MLX dispatch benchmark;
- segmented matrix multiplication in MLX;
- custom Metal kernels only if ordinary tensor operations remain the measured bottleneck.

The reference implementation remains the readable definition of the algorithm. Optimized backends must be tested against it.

## Phase 12 — Confirm, analyze, and publish

Scale to M162 or M251 only when the smaller experiment has a stable, repeated effect.

For the final result:

- predeclare the hypothesis and primary metrics;
- use multiple seeds where affordable;
- report confidence intervals or variation;
- include failed runs and tuning budgets;
- publish configs, manifests, small logs, plots, and analysis;
- keep large checkpoints and datasets external;
- repeat the novelty search immediately before making research claims.

An informative negative result is acceptable. The project succeeds scientifically if it identifies, with controlled evidence, when sparse capacity or stability-aware routing helps, fails, or loses its algorithmic gain to Apple-specific dispatch overhead.

## Tomorrow: exact first session

The first session should remain small and conceptual.

1. Read sections 5, 8, and 9 of the research plan: fair experimental design, architecture proposal, and hard exit criteria.
2. Inspect `foundation/minillm/model.py`, `attention.py`, `train.py`, and their tests. Do not modify them.
3. Draw the D20 forward pass and annotate every tensor shape.
4. Derive the D20 parameter count by hand, separating embeddings, attention, norms, and SwiGLU.
5. Write a short design note in your own words describing the model API, tensor convention, and why D20 exists.
6. Decide the first implementation unit: configuration plus parameter-count verification.
7. Before coding, explain the design back to the teacher and resolve any incorrect assumptions.

The first code should be deliberately modest: the model configuration and a testable parameter-count calculation. RMSNorm comes next. Attention should not be the first file written.

## Definition of project success

### Engineering success

- A readable from-scratch LM stack trains dense and sparse 20–250M models on MPS.
- Runs resume reproducibly and record complete provenance.
- Sparse dispatch is correct, measured, and optimized enough for controlled experiments.

### Scientific success

- M133 improves on D50 at matched active compute across repeated runs with tolerable wall-clock overhead.

### Strong research success

- M133-S improves over standard M133 in BPB and controlled repetition metrics without increasing active expert compute.
- The improvement is mechanistically linked to residual dynamics and useful route changes.
- The result survives more than one scale and more than one seed.

The branch should be treated as a laboratory notebook with executable evidence: small commits, explicit hypotheses, reproducible configurations, and honest conclusions.
