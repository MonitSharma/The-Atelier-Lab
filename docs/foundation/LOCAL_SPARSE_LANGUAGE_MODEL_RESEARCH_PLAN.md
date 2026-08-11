> Imported from the Deep Research result received on 11 August 2026.
>
> This is a working research plan, not a record of validated results. Treat numerical estimates and novelty claims as hypotheses until reproduced locally and verified against primary sources.

# The Atelier Lab — Local Sparse Language Model Research Plan

**Research question:**
*Can a stability-aware, difficulty-routed sparse language model achieve better language-modeling quality and lower repetition than a dense model of comparable active parameter count and compute, while remaining efficient to train on Apple Silicon?*

**Assessment date:** 11 August 2026.

I would pursue this project. The important qualification is that the scientifically useful project is **not “train the largest model that fits in 36 GB.”** The useful project is a carefully controlled 50M–250M-parameter experimental system in which dense and sparse models can be trained repeatedly, instrumented heavily, and compared under matched compute.

I use three levels of confidence below:

* **Established** — supported by primary literature or official technical documentation.
* **Engineering estimate** — calculated from the hardware constraints and the local throughput figures in the question.
* **Research hypothesis** — plausible but requiring experimental validation.

---

# 1. Executive recommendation

## Recommendation

**Yes. This is a sensible research project for one M3 Pro / 36 GB Mac, provided the goal is algorithmic understanding and controlled small-model research rather than competitive frontier pretraining.**

The machine is unusually suitable for this type of work because the models under consideration are small enough that parameter memory is manageable, while the unified-memory architecture removes the conventional CPU↔discrete-GPU memory boundary. MLX is explicitly designed around Apple Silicon unified memory, while PyTorch exposes MPS as its Metal-backed GPU device. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/notes/mps.html?utm_source=chatgpt.com)][1])

### Technically possible

On 36 GB unified memory you can plausibly:

| Experiment                         |                         Technically possible? |
| ---------------------------------- | --------------------------------------------: |
| 20M dense                          |                                        Easily |
| 50M dense                          |                                        Easily |
| 100M dense                         |                                           Yes |
| 200M dense                         |                                           Yes |
| 300M dense                         |                                           Yes |
| 150–300M total, top-1 MoE          |                                           Yes |
| 1B dense forward/inference         |                                           Yes |
| 1B dense full AdamW training       | Possibly, with careful batching/checkpointing |
| Meaningful repeated 1B pretraining |                           **No, practically** |

The striking point is that **memory does not become the main constraint around 100–300M parameters**. Training time and hardware utilization become limiting first.

### Practically worthwhile

I would divide the project into three bands:

* **20M:** debugging, mathematical validation, routing experiments.
* **45–110M:** primary research-development scale.
* **130–300M total sparse:** final MoE research scale.

A 1B model should exist only as a **stress-test boundary** for the framework.

### Central architectural recommendation

Start from a modern but deliberately uncomplicated decoder:

**Pre-RMSNorm → causal attention → RoPE → SwiGLU → tied embeddings**, with GQA optional rather than fundamental.

RMSNorm, gated FFNs such as SwiGLU, RoPE, and GQA each have strong primary-literature precedents. ([[arXiv](https://arxiv.org/abs/2002.05202?utm_source=chatgpt.com)][2])

Then replace selected/all dense FFNs with:

> **4 experts, top-1 routing, no token dropping, Switch-style balancing, ST-MoE-style router stabilization.**

Switch demonstrated that top-1 routing can simplify sparse models substantially, while ST-MoE focused specifically on sparse-model stability. ([[arXiv](https://arxiv.org/abs/2101.03961?utm_source=chatgpt.com)][3])

I would **not start with top-2 Mixtral-style routing**. It roughly doubles expert FFN execution per token relative to top-1 with the same expert width and makes the Apple dispatch problem harder.

### Most interesting research direction

My preferred thesis is:

> **A top-1 sparse language model can use an inference-available dynamical-stability signal to improve routing decisions for difficult tokens, producing better validation BPB and lower repetition at matched executed compute than both a conventional top-1 MoE and an active-parameter-matched dense model.**

The strongest candidate signal is not “difficulty” as an abstract label. It is something measurable from the Transformer itself, such as the **relative residual update magnitude**

[
s_\ell(x)=
\log\left(
\epsilon+
\frac{|\Delta h_\ell(x)|*2}
{|h*\ell(x)|_2+\epsilon}
\right).
]

This connects the routing hypothesis to Transformer dynamics rather than adding another opaque difficulty predictor.

There is already substantial overlap around token-dependent computation: Mixture-of-Depths allocates computation non-uniformly across tokens; DynaMoE explicitly routes according to token difficulty; very recent EntropyMoE uses entropy itself as a routing coordinate; and 2026 work reports that standard routers can systematically misroute fragile tokens. ([[arXiv](https://arxiv.org/abs/2404.02258?utm_source=chatgpt.com)][4])

Therefore, **“difficulty-aware routing” alone is not a viable novelty claim**. The contribution needs to be the particular stability variable, routing mechanism, controlled compute-matched evidence, and mechanistic analysis.

---

# 2. Realistic model scale

## 2.1 Memory assumptions

For the conservative reference implementation, assume:

* FP32 parameters: **4 bytes/parameter**
* FP32 gradients: **4 bytes/parameter**
* AdamW first moment: **4 bytes/parameter**
* AdamW second moment: **4 bytes/parameter**

Hence persistent state after Adam has initialized is approximately

[
M_{\text{persistent}}
=====================

# (4+4+4+4)P

16P\text{ bytes}.
]

PyTorch's own optimizer-memory discussion separates parameter, gradient, and Adam-state storage in this way; optimizer implementations can also create temporary intermediates during `step()`. ([[PyTorch Documentation](https://docs.pytorch.org/tutorials/intermediate/optimizer_step_in_backward_tutorial.html?utm_source=chatgpt.com)][5])

This excludes:

* activations,
* attention workspaces,
* allocator caching,
* MPS/Metal driver allocations,
* dataloader buffers,
* temporary optimizer tensors,
* compiled kernels.

### Persistent training state

| Parameters | Weights | Gradients | Adam m+v | Persistent total | FP32 model+optimizer checkpoint* |
| ---------: | ------: | --------: | -------: | ---------------: | -------------------------------: |
|        20M | 0.08 GB |      0.08 |     0.16 |      **0.32 GB** |                         ~0.24 GB |
|        50M |    0.20 |      0.20 |     0.40 |      **0.80 GB** |                         ~0.60 GB |
|       100M |    0.40 |      0.40 |     0.80 |      **1.60 GB** |                         ~1.20 GB |
|       200M |    0.80 |      0.80 |     1.60 |      **3.20 GB** |                         ~2.40 GB |
|       300M |    1.20 |      1.20 |     2.40 |      **4.80 GB** |                         ~3.60 GB |
|         1B |    4.00 |      4.00 |     8.00 |      **16.0 GB** |                         ~12.0 GB |

*weights + Adam moments; scheduler/RNG/metadata add little relative to the model.

A weight-only FP32 checkpoint is (4P) bytes; FP16/BF16 weights are (2P) bytes.

Thus a 300M model is **not remotely a 36-GB parameter-storage problem**. The real uncertainty is activation plus runtime allocation.

PyTorch exposes both tensor allocation and Metal-driver allocation separately through `torch.mps.current_allocated_memory()` and `torch.mps.driver_allocated_memory()`, as well as the Metal device's `recommended_max_memory()`. These should become part of the benchmark logger. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/generated/torch.mps.driver_allocated_memory.html?utm_source=chatgpt.com)][6])

I would initially treat **24–28 GB as an engineering safety envelope rather than a target** and determine the actual limit empirically. That number is not an Apple guarantee.

---

## 2.2 Activations

Activation memory is more implementation-specific than parameter memory.

For a reasonably efficient Pre-Norm decoder without storing an (T\times T) attention matrix, a useful **engineering estimate** is

[
M_A
\approx
cLBTd,b,
]

where

* (L) = layers,
* (B) = microbatch sequences,
* (T) = context,
* (d) = model width,
* (b) = bytes/activation,
* (c\approx12-20) is an empirical bookkeeping factor for the tensors saved by autograd.

Using (c=16) and two-byte activations gives approximately:

| Model          | Example microbatch | Rough saved activations |
| -------------- | ------------------ | ----------------------: |
| 50M, 12×512    | B=8, T=1024        |                ~1.61 GB |
| 100M, 20×640   | B=4, T=1024        |                ~1.68 GB |
| 162M-total MoE | B=4, T=1024        |  ~0.91 GB + MoE buffers |
| 251M-total MoE | B=4, T=1024        |  ~1.34 GB + MoE buffers |

These numbers are deliberately **not guarantees**. Measure the actual graph.

Naively materializing attention probabilities introduces terms scaling approximately as

[
O(BHT^2),
]

which becomes expensive quickly. Use the native scaled-dot-product-attention path where practical.

Activation checkpointing can reduce memory by recomputing forward operations during backward; PyTorch explicitly documents it as a compute-for-memory trade. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/checkpoint.html?utm_source=chatgpt.com)][7])

For 50–100M models I would initially **avoid checkpointing**. You want the cleanest possible performance measurements first.

---

## 2.3 Sequence length and batch size

Recommended progression:

| Stage                       |  Context |
| --------------------------- | -------: |
| Unit tests                  |   64–256 |
| Single-batch overfit        |  128–512 |
| Tiny corpus                 |      512 |
| Baseline                    | **1024** |
| Optional context experiment |     2048 |

Do not make 4096+ context an early objective. It changes the compute balance toward attention and adds another research variable.

I recommend targeting a global batch measured in **tokens**, not sequences.

A good initial target is:

[
B_{\text{global}}\approx131,072\text{ tokens/update}.
]

For example:

[
8 \times 1024 \times 16
=======================

131,072
]

with microbatch 8 and accumulation 16.

For a 100M model you might instead use:

[
4\times1024\times32.
]

Gradient accumulation reduces peak activation memory but does **not** reduce total training FLOPs. Extremely small microbatches may also reduce GPU utilization.

---

## 2.4 Throughput calibration

Your two existing observations provide a useful local calibration:

* 73M → **18,700 tok/s**
* 286M → **4,470 tok/s**

A simple two-point power fit gives

[
R(P)\approx
\frac{1.678\times10^6}{P^{1.048}}
]

with (P) in millions of parameters.

That is only an extrapolation from two points, not a performance law.

### Predicted dense throughput

| Model | Power-fit tok/s | More conservative sustained expectation |
| ----- | --------------: | --------------------------------------: |
| 20M   |           72.6k |                              **40–70k** |
| 50M   |           27.8k |                              **20–30k** |
| 100M  |           13.4k |                              **10–15k** |
| 200M  |            6.5k |                                **5–8k** |
| 300M  |           4.25k |                              **3.5–5k** |
| 1B    |           1.20k |                            **0.8–1.4k** |

The “sustained” range allows for dataloading, evaluation, checkpointing, thermal behavior, and differences between the old and new implementation.

It should be regarded as **planning data until you rerun the benchmark with the new code**.

---

## 2.5 Practical token budgets

Chinchilla found that compute-optimal model size and training-token count should scale together under its experimental regime. A commonly useful planning anchor around those results is roughly tens of tokens per parameter, but it is not a universal optimum for small models, modern datasets, or MoEs. ([[arXiv](https://arxiv.org/abs/2203.15556?utm_source=chatgpt.com)][8])

Using **20 tokens/parameter only as a planning reference** gives:

| Dense | Token budget | Approx. sustained wall time |
| ----- | -----------: | --------------------------: |
| 20M   |         0.4B |                    **~2 h** |
| 50M   |           1B |                   **~13 h** |
| 100M  |           2B |           **~55 h / 2.3 d** |
| 200M  |           4B |                  **~9.5 d** |
| 300M  |           6B |                   **~22 d** |
| 1B    |          20B |                  **~256 d** |

This table explains the project boundaries better than the memory table.

### Therefore

**50M** can be run frequently.

**100M** can be trained seriously.

**200M** should be reserved for selected experiments.

**250–300M** should be a final experiment, not the development loop.

**1B is scientifically uneconomical on this laptop.**

---

## 2.6 Sparse models

For an MoE, distinguish carefully:

[
P_{\rm total}
\neq
P_{\rm active}.
]

A 4-expert top-1 FFN adds four copies of expert parameters to storage, but only one expert FFN is executed per token.

That gives sparse models their fundamental parameter/compute separation. Switch, Mixtral, DeepSeekMoE and OLMoE exploit versions of this principle. ([[arXiv](https://arxiv.org/abs/2101.03961?utm_source=chatgpt.com)][3])

However, **active parameter count is not exactly equal to computational cost** because:

* attention remains dense,
* vocabulary logits remain dense,
* routing costs something,
* gather/sort/scatter costs something,
* optimizer updates can touch all experts,
* all expert weights remain resident.

This distinction matters considerably on Apple Silicon.

My rough expectations for a well-vectorized top-1 implementation are:

| MoE               | Total | Active | Expected range |
| ----------------- | ----: | -----: | -------------: |
| First matched MoE |  133M |  48.5M |  ~12–24k tok/s |
| Medium            |  162M |    59M |        ~11–20k |
| Final             |  251M |    86M |         ~8–14k |

These are **uncertain engineering targets**, not existing benchmarks.

---

# 3. Apple Silicon training

## PyTorch MPS versus MLX

| Dimension                | PyTorch MPS          | MLX                                                  |
| ------------------------ | -------------------- | ---------------------------------------------------- |
| Research transparency    | **Excellent**        | Excellent                                            |
| PyTorch ecosystem        | **Excellent**        | Limited                                              |
| Autograd familiarity     | **Excellent**        | Good                                                 |
| Apple-first design       | Good and improving   | **Excellent**                                        |
| Unified memory semantics | Indirect through MPS | **First-class design**                               |
| Fused Apple kernels      | Increasing           | **Core strength**                                    |
| MoE-specific primitives  | General tensor ops   | `segmented_mm`, gather/sort + custom Metal promising |
| Portability              | **High**             | Apple-oriented                                       |
| Reference backend        | **Recommended**      | No                                                   |
| Optimization backend     | Later                | **Recommended later**                                |

PyTorch 2.13's MPS backend continues to receive substantial Apple-Silicon work; the 2.13 release added handwritten Metal paths and FlexAttention support on MPS, including GQA-related paths. ([[PyTorch](https://pytorch.org/blog/pytorch-2-13-release-blog/?utm_source=chatgpt.com)][9])

MLX explicitly exposes unified-memory behavior, graph compilation, fast RMSNorm/RoPE/SDPA operations, custom Metal kernels, and segmented matrix multiplication. ([[ML Explore](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html?utm_source=chatgpt.com)][10])

### My recommendation

Build:

```text
model/
    transformer.py
    attention.py
    ffn.py
    moe.py
    router.py

backend/
    torch_backend/
```

first.

Only once the scientific implementation is frozen should you create:

```text
backend/
    mlx_backend/
```

Do **not** allow the MLX port to become the canonical definition of the algorithm.

---

## Supported and unsupported operations

A static list of “unsupported MPS operations” is a poor foundation because coverage changes between PyTorch versions. Current PyTorch documentation provides an MPS device interface and an environment-controlled fallback mechanism; the recent releases continue expanding native Metal support. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/notes/mps.html?utm_source=chatgpt.com)][1])

For research runs I recommend:

> **Fail on unsupported MPS operations rather than silently benchmarking CPU fallbacks.**

Specifically, treat:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1
```

as a debugging convenience, not a benchmark configuration. The fallback variable is documented by PyTorch. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/mps_environment_variables.html?utm_source=chatgpt.com)][11])

Your CI/test harness should explicitly exercise every MoE primitive on MPS.

---

## Precision

Start correctness tests in **FP32**.

Then separately benchmark:

1. FP32
2. FP16 parameters/operations where stable
3. autocast if the installed MPS release supports the exact operator set adequately

I would keep these numerically sensitive components in FP32 where feasible:

* router logits,
* softmax/logsumexp,
* auxiliary routing losses,
* final cross-entropy accumulation,
* diagnostic norm calculations.

Do **not** assume that every BF16/FP16 combination supported elsewhere in PyTorch has identical MPS behavior. Probe your actual version.

MLX exposes FP16/BF16-capable operations and its optimized SDPA implementation, making lower-precision experiments particularly interesting later. ([[ML Explore](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.fast.scaled_dot_product_attention.html?utm_source=chatgpt.com)][12])

---

## CPU/GPU synchronization

A major performance trap is accidental synchronization.

Avoid inside the training hot path:

```python
loss.item()
tensor.cpu()
tensor.numpy()
print(tensor)
```

at every step.

Instead:

* accumulate device metrics,
* synchronize every 50–200 steps,
* evaluate on fixed intervals,
* time with MPS events or explicit synchronized boundaries.

PyTorch provides MPS events specifically for device timing and synchronization, and MPS signpost tracing can be examined through Instruments. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/generated/torch.mps.event.Event.html?utm_source=chatgpt.com)][13])

---

## Static versus dynamic shapes

This is especially important for MoE.

Standard token routing produces dynamically sized expert batches:

```text
expert 0: 1137 tokens
expert 1: 982
expert 2: 1014
expert 3: 963
```

That is convenient mathematically but awkward computationally.

For PyTorch MPS, compare:

### A. Dynamic packed dispatch

```text
route
→ sort tokens by expert
→ contiguous expert segments
→ expert GEMMs
→ inverse permutation
```

### B. Static capacity buffers

Allocate something like:

```text
[E, capacity, d]
```

and pad unused slots.

The latter wastes arithmetic but can give more regular kernel shapes.

MLX's `compile()` can fuse work and reduce graph/runtime overhead, but changing input shapes can cause recompilation; its documentation explicitly discusses shape-sensitive compilation and `shapeless=True`. ([[ML Explore](https://ml-explore.github.io/mlx/build/html/usage/compile.html?utm_source=chatgpt.com)][14])

Therefore fixed sequence length, fixed microbatch and **a few expert-capacity buckets** are likely to work better than arbitrary shapes.

---

## Will MoE dispatch perform well on MPS?

**Uncertain.**

There is currently no primary evidence I would trust enough to promise that a custom small MoE will achieve dense-active-model throughput parity on MPS.

The likely problem is not the FFN matrix multiplication. It is:

[
\text{top-k}
+
\text{sort}
+
\text{gather}
+
\text{small GEMMs}
+
\text{scatter}.
]

With four experts, individual expert matrices remain reasonably large, which helps. With 16, 32, or 64 experts your laptop would likely spend too much time manipulating small token groups.

That is another reason to choose **E=4**.

MLX may ultimately be a better optimization substrate because it exposes `segmented_mm` and custom JIT Metal kernels directly. ([[ML Explore](https://ml-explore.github.io/mlx/build/html/python/ops.html?utm_source=chatgpt.com)][15])

---

# 4. Mixture-of-Experts theory and practice

The classic sparsely gated MoE idea predates modern Transformer MoEs; Shazeer et al. demonstrated conditional activation of a subset of a much larger parameter pool. GShard then integrated sparse experts into massive distributed Transformer systems. ([[arXiv](https://arxiv.org/abs/2006.16668?utm_source=chatgpt.com)][16])

## Router

For hidden state (h),

[
z=W_rh
]

are the **router logits**.

Then

[
p_i=
\frac{\exp(z_i)}
{\sum_j\exp(z_j)}.
]

For top-(k),

[
S(h)=\operatorname{TopK}(p,k).
]

The MoE output is conceptually

[
y=
\sum_{i\in S(h)}
\tilde p_i E_i(h).
]

---

## Top-1 versus top-2

### Top-1

One expert executes:

[
y=E_{i^*}(h)
]

possibly multiplied by the routing score.

Advantages:

* one FFN execution,
* simplest dispatch,
* lowest memory traffic,
* easier matched-active-compute experiment.

Switch Transformer was specifically motivated by simplifying MoE routing toward a one-expert-per-token formulation. ([[arXiv](https://arxiv.org/abs/2101.03961?utm_source=chatgpt.com)][3])

### Top-2

Two experts execute and outputs are combined.

Benefits can include:

* redundant paths,
* richer mixtures,
* less brittle routing.

But the expert compute becomes roughly twice that of top-1 for equal expert width.

Mixtral uses sparse expert activation with two experts per token; its reported architecture is an important modern top-2 reference. DeepSeekMoE instead explores finer expert segmentation plus shared experts. ([[arXiv](https://arxiv.org/abs/2401.06066?utm_source=chatgpt.com)][17])

For Atelier: **top-1 first.**

---

## Load balancing

Without additional pressure, the router may send most tokens to a small number of experts.

A Switch-style balancing objective can be represented as

[
L_{\rm balance}
===============

E\sum_i f_i\bar p_i
]

where

* (f_i) is the fraction of tokens assigned to expert (i),
* (\bar p_i) is its average router probability.

You should log the raw LM loss and every router loss independently.

ST-MoE is particularly relevant because its primary focus is sparse-model training stability rather than only scale. ([[arXiv](https://arxiv.org/abs/2202.08906?utm_source=chatgpt.com)][18])

---

## Expert capacity

Distributed MoEs often define

[
C
=

\left\lceil
\frac{Nk}{E}
\times
\text{capacity factor}
\right\rceil.
]

Overflow may cause **token dropping**.

For Atelier's single-device research:

> **Do not drop tokens initially.**

There is no inter-device all-to-all buffer requiring a hard communication capacity.

Process every token and make dispatch efficiency a separate engineering question.

This removes an unnecessary confound.

---

## Expert collapse

Collapse means one or a few experts dominate traffic while others receive inadequate data/gradient.

Measure:

[
u_i=
\frac{n_i}{N}
]

along with:

* coefficient of variation,
* Gini coefficient,
* minimum expert share,
* maximum expert share,
* dead-expert windows.

Do not define “dead” from one minibatch.

For example:

> dead if utilization remains below 5% of uniform expected utilization for 10 consecutive evaluation windows.

---

## Routing entropy

Per-token:

[
H(h)=
-\sum_i p_i(h)\log p_i(h).
]

Normalized:

[
H_N=\frac{H}{\log E}.
]

Interpretation:

* (H_N\rightarrow0): confident router;
* (H_N\rightarrow1): nearly indifferent router.

But also measure **aggregate traffic entropy**. A router can be individually confident yet globally balanced.

Entropy itself is now an active adaptive-routing research direction; a very recent EntropyMoE paper routes using entropy-related information, and GeMoE uses gating entropy to vary expert activation. ([[arXiv](https://arxiv.org/abs/2608.06398?utm_source=chatgpt.com)][19])

So again, **entropy routing alone is no longer a convincing novelty direction.**

---

## Shared experts

DeepSeekMoE separates some always-active “shared” experts from routed experts, motivated by capturing common knowledge separately from specialist capacity. ([[arXiv](https://arxiv.org/abs/2401.06066?utm_source=chatgpt.com)][17])

This is interesting but should be a later ablation.

A shared expert:

* increases active FLOPs,
* complicates matching,
* weakens the elegant dense↔MoE control experiment.

---

## Expert specialization

Be careful with this term.

Routing differences do not automatically imply semantic specialists.

Recent 2026 research questions simplistic interpretations of expert specialization and argues that routing patterns are deeply tied to hidden-state geometry. ([[arXiv](https://arxiv.org/abs/2604.09780?utm_source=chatgpt.com)][20])

Therefore measure specialization operationally:

* token-frequency distribution,
* punctuation/code/numeric fractions,
* POS where available,
* input entropy,
* per-token baseline loss,
* residual-update magnitude,
* expert-output cosine similarity,
* activation PCA.

Then ask whether these differ statistically between experts.

---

## Major approaches

| Work                       | Main idea                                | Useful here?            |
| -------------------------- | ---------------------------------------- | ----------------------- |
| Sparse MoE, Shazeer et al. | conditional expert activation            | Foundational            |
| GShard                     | MoE + massive sharding                   | Theory yes; systems no  |
| Switch                     | top-1 simplification                     | **Very useful**         |
| ST-MoE                     | stability and transfer                   | **Very useful**         |
| Expert Choice              | experts select tokens / variable compute | Interesting later       |
| StableMoE                  | routing-stability problem                | Relevant                |
| Mixtral                    | modern top-2 sparse decoder              | Reference               |
| DeepSeekMoE                | fine-grained + shared experts            | Later ablation          |
| OLMoE                      | fully open MoE training                  | **Excellent reference** |
| Mixture-of-Depths          | token-dependent depth                    | Novelty comparator      |
| DynaMoE                    | difficulty-adaptive compute              | Novelty comparator      |

OLMoE is especially useful because its model, code, data, training information and checkpoints were released explicitly to support open study of sparse-model training. ([[arXiv](https://arxiv.org/abs/2409.02060?utm_source=chatgpt.com)][21])

---

# 5. Fair experimental design

This is where I think Atelier can become unusually strong.

## The matched “triangle”

I would construct these three architectures:

### A. D50

**48.464M dense**

### B. D133

**133.448M dense**

### C. M133

**133.423M total MoE / 48.488M active**

Then introduce:

### D. M133-S

same MoE, except your stability-aware router.

This produces a particularly clean design:

[
P_{\rm active}(M133)
\approx
P(D50)
]

and

[
P_{\rm total}(M133)
\approx
P(D133).
]

So **one MoE simultaneously matches the small dense model in active parameter count and the large dense model in total parameter count.**

That is far stronger scientifically than comparing arbitrary model sizes.

---

## Controls

Hold constant:

* exact tokenizer,
* exact dataset snapshot,
* byte-level train/validation split,
* document ordering,
* token ordering,
* context length,
* total training tokens,
* global batch in tokens,
* optimizer family,
* betas,
* epsilon,
* weight decay,
* gradient clipping,
* warmup fraction,
* schedule shape,
* evaluation intervals,
* checkpoint intervals,
* hardware,
* OS,
* PyTorch version,
* precision.

Pythia is an excellent precedent for controlled scaling experiments because models of different sizes were trained on public data in the exact same order and released with dense checkpoint histories. ([[arXiv](https://arxiv.org/abs/2304.01373?utm_source=chatgpt.com)][22])

---

## Learning-rate fairness

“Same LR” sounds fair but is not necessarily fair.

I suggest:

### Development phase

Each architecture receives the **same tuning budget**, e.g.

[
{0.7,1.0,1.4}\times \eta_0.
]

Lock the winning recipe before final experiments.

A more sophisticated future option is μ-parameterization/μTransfer, but I would not introduce it during the first MoE experiments.

---

## Match both parameters and FLOPs

Do not rely solely on “active parameters.”

Calculate approximate operator FLOPs for:

* Q/K/V/O projections,
* attention score computation,
* FFN,
* router,
* output vocabulary projection.

The common approximation

[
C\approx 6ND
]

is useful at scale, but precise architecture comparisons should account for attention and vocabulary projection explicitly.

---

## Evaluation metrics

### Language modeling

**Validation cross-entropy**

[
L=-\frac1N\sum_t\log p(x_t|x_{<t})
]

Primary metric.

**Perplexity**

[
PPL=e^L.
]

Use it only when tokenization is identical.

**Bits per byte**

[
BPB=
\frac{\sum_t -\ln p_t}
{N_{\rm bytes}\ln2}.
]

This should be your tokenizer-independent quality metric.

---

## Performance

Log:

* training tokens/s,
* forward tokens/s,
* generation tokens/s,
* peak tensor memory,
* Metal driver memory,
* wall-clock hours,
* tokens/joule if measurable.

For joules, use an external wall-energy meter for final claims if possible. SoC-level estimates are useful diagnostically but should not be presented as precise GPU-only energy measurements.

---

## Repetition

This requires careful methodology because decoding itself can radically alter repetition even with an unchanged model. Holtzman et al. demonstrated this explicitly. ([[arXiv](https://arxiv.org/abs/1904.09751?utm_source=chatgpt.com)][23])

Evaluate every model under identical:

1. greedy decoding;
2. temperature (=1);
3. fixed top-p, e.g. 0.9;
4. same prompts;
5. same generation length.

Measure:

[
R_n
===

1-
\frac{|\text{unique ngrams}|}
{|\text{all ngrams}|}.
]

Include:

* repeated 3-gram fraction,
* repeated 4-gram fraction,
* longest repeated substring,
* immediate-loop frequency,
* distinct-1/2/3,
* optionally MAUVE.

Do **not** introduce unlikelihood training into the primary comparison; it is already known specifically to affect repetition and would confound the architectural question. ([[arXiv](https://arxiv.org/abs/1908.04319?utm_source=chatgpt.com)][24])

---

## MoE metrics

For every layer:

* expert traffic (u_i),
* load CV,
* Gini,
* router entropy,
* router max probability,
* router-logit RMS/max,
* dead-expert rate,
* token switches between checkpoints,
* expert-output norms,
* specialization descriptors.

And for the proposed research:

[
I(s_\ell;\text{expert})
]

or simpler conditional statistics between stability signal (s) and routes.

---

## Scientific headline metrics

I would predeclare:

1. **validation BPB at fixed tokens**
2. **validation BPB at fixed active FLOPs**
3. **wall-clock to target BPB**
4. **repeat-4 rate under fixed decoding**
5. **training tokens/joule**
6. **router balance and dead-expert rate**

Quality-per-FLOP is best presented as a **Pareto curve**, rather than inventing a fragile scalar ratio.

---

# 6. Physics-inspired research directions

The physics analogy should be used where it produces a **measurable dynamical quantity**, not decorative terminology.

Recent work has explicitly studied Transformer dynamics through order/chaos regimes and Lyapunov-like quantities, while DeepNorm, ReZero and related stabilization work connect residual structure and initialization to trainability. ([[arXiv](https://arxiv.org/abs/2203.00555?utm_source=chatgpt.com)][25])

## 6.1 Relative residual-update routing — strongest candidate

### Hypothesis

Tokens undergoing unusually large representational updates are dynamically “difficult” and benefit more from specialized computation.

Define:

[
r_\ell=
\frac{|\Delta h_\ell|}
{|h_\ell|+\epsilon}.
]

### Minimal implementation

Standardize with an EMA:

[
z_r=
\frac{\log(r+\epsilon)-\mu_\ell}
{\sigma_\ell+\epsilon}.
]

Modify router logits:

[
g=
W_r,\mathrm{RMSNorm}(h)
+
a_\ell z_r
]

where (a_\ell\in\mathbb R^E).

This adds essentially negligible parameters.

### Baseline

Normal top-1 linear router.

### Prediction

High-(r) tokens:

* have higher next-token loss,
* route differently,
* derive more benefit from specialization.

M133-S should improve BPB and repeat rate without materially changing active FLOPs.

### Failure modes

* (r) correlates only with scale/noise.
* RMSNorm already removes the useful information.
* signal comes too late in the block.
* router ignores (a_\ell).
* experts simply partition by frequency.

### Difficulty

**Medium.**

### Novelty assessment

**Promising candidate, not proven novel.**

My literature audit found substantial adjacent work on difficulty routing, entropy routing, norm-based adaptive computation, routing instability and counterfactual misrouting, including DynaMoE, EntropyMoE, Mixture-of-Depths, Equifinality and recent misrouting analysis. ([[arXiv](https://arxiv.org/abs/2502.12325?utm_source=chatgpt.com)][26])

I did **not** find in this audit an exact primary-language-model study using the *relative Transformer residual update as an inference-available additive router coordinate*, trained from scratch in a compute-matched sparse LM experiment. That is **not evidence of global novelty**, and another audit should be done immediately before publication.

---

## 6.2 Critical residual scaling

### Hypothesis

Controlling residual-branch scale keeps propagation nearer a stable regime and prevents large early-training fluctuations.

### Minimal implementation

Compare

[
h_{l+1}=h_l+F_l(h_l)
]

with

[
h_{l+1}=h_l+\alpha_LF_l(h_l).
]

Possibly learn (\alpha_l) or initialize it using a depth-dependent rule.

### Prediction

* fewer gradient spikes,
* more constant activation variance across depth,
* more stable MoE router entropy.

### Failure

At only 12–20 layers, ordinary Pre-Norm may already be sufficiently stable.

### Difficulty

Low.

### Novelty

**Reproduction/diagnostic, not new.**

DeepNorm and ReZero already establish strong precedent for residual scaling as a stabilization mechanism. ([[arXiv](https://arxiv.org/abs/2203.00555?utm_source=chatgpt.com)][25])

---

## 6.3 Jacobian / singular-value diagnostics

Study

[
J_\ell=
\frac{\partial h_{\ell+1}}
{\partial h_\ell}.
]

Perfect dynamical isometry would place singular values near 1.

### Minimal experiment

Do not construct the enormous Jacobian during training.

For small diagnostic batches use:

* JVP,
* VJP,
* power iteration,
* Hutchinson trace estimates,
* exact SVD only for tiny models.

### Prediction

Stable models should avoid extreme singular-value spread.

### Failure

Local Jacobian properties may correlate poorly with final LM quality.

### Difficulty

High.

### Novelty

Mostly mechanistic reproduction unless tied tightly to routing.

---

## 6.4 Router-temperature dynamics

[
p_i=
\operatorname{softmax}(z_i/T).
]

### Hypothesis

High (T) early encourages exploration and avoids collapse; lower (T) later permits specialization.

### Minimal implementation

Fixed, cosine, or learned (T_\ell(t)).

### Predictions

A useful schedule should show:

* high early traffic entropy,
* later expert differentiation,
* lower validation loss without dead experts.

### Failure

Load-balancing loss may already provide enough exploration.

### Difficulty

Low.

### Novelty

Low. Routing entropy and temperature have extensive precedent, and recent research explicitly studies phase-like routing dynamics. ([[arXiv](https://arxiv.org/abs/2604.04230?utm_source=chatgpt.com)][27])

---

## 6.5 Spectral expert specialization

Construct expert activation covariance

[
C_i=
\mathbb E[(h-\mu_i)(h-\mu_i)^T]
]

and inspect its leading eigenspectrum.

### Hypothesis

Real specialization should produce different low-dimensional subspaces, not merely different token counts.

### Measure

* PCA spectrum,
* principal-angle distance,
* expert-output cosine similarity,
* effective rank.

### Prediction

Specialization increases with depth/training and correlates with quality gain.

### Failure

All experts learn redundant transformations.

### Difficulty

Medium.

### Novelty

Primarily analysis/reproduction; recent work already questions and geometrically analyzes expert specialization. ([[arXiv](https://arxiv.org/abs/2604.09780?utm_source=chatgpt.com)][20])

---

## 6.6 Reversible layers

Reversible architectures reconstruct activations instead of storing all of them.

### Hypothesis

They could allow larger sequences/batches under fixed memory.

### But on this machine

Memory is unlikely to be the binding constraint at the scientifically useful scales.

The additional recomputation therefore attacks the wrong bottleneck.

### Recommendation

**Do not prioritize.**

### Novelty

Reproduction.

---

## 6.7 Energy-based routing interpretation

Write:

[
E_i(h)=-z_i(h)
]

and

[
p_i(h)
======

\frac{e^{-E_i/T}}
{\sum_j e^{-E_j/T}}.
]

This gives a Boltzmann-like interpretation.

### Useful experiment

Sweep (T), load-balance pressure and initialization.

Measure:

* router entropy,
* expert occupancy,
* specialization,
* BPB.

### Research question

Are there sharp transitions between:

1. disordered/high-entropy routing,
2. balanced specialization,
3. collapsed routing?

Recent 2026 work directly reports multi-phase expert-routing behavior, so phase-transition analysis itself is **not clean novelty**, though reproducing it in a from-scratch small model could be illuminating. ([[arXiv](https://arxiv.org/abs/2604.04230?utm_source=chatgpt.com)][27])

---

## 6.8 Adaptive expert count

Use routing uncertainty to choose (k=1) or (k=2).

Very interesting scientifically.

But **do it later**.

Mixture-of-Depths already demonstrates dynamic token compute, and GeMoE and DynaMoE introduce uncertainty/difficulty-based adaptive activation. ([[arXiv](https://arxiv.org/abs/2404.02258?utm_source=chatgpt.com)][4])

The field has become crowded enough that this would require a stronger twist than “hard tokens get more experts.”

---

# 7. Best project thesis

I recommend narrowing the thesis to:

> **Stability-Aware Sparse Language Modeling on a Single Accelerator:**
> At matched executed compute, can a four-expert top-1 Transformer whose router is augmented with a cheap dynamical-stability signal outperform both a conventional sparse router and a dense Transformer in language-modeling quality and repetition, and can the improvement be explained through token difficulty, residual dynamics, and expert specialization?

The key scientific chain would be:

[
\text{residual dynamics}
\rightarrow
\text{predict token difficulty}
\rightarrow
\text{change routing}
\rightarrow
\text{specialized computation}
\rightarrow
\text{lower loss/repetition}.
]

Each arrow is falsifiable.

That is important.

A negative result such as

> residual instability predicts difficulty, but routing on it produces no advantage

would still be scientifically meaningful.

So would:

> sparse capacity helps at equal active FLOPs but does not reduce repetition.

Or:

> MoE is algorithmically better but Metal dispatch eliminates its wall-clock advantage.

All three are stronger research results than merely demonstrating that a custom MoE trains.

---

# 8. Architecture proposal

Parameter calculations below assume:

* tied token/input-output embeddings,
* no material biases,
* head dimension 64,
* SwiGLU,
* GQA where specified.

For GQA,

[
P_{\rm attn/layer}
\approx
2d^2+2d d_{\rm kv}.
]

SwiGLU contributes approximately

[
P_{\rm FFN/layer}
\approx
3dd_{\rm ff}.
]

---

## 8.1 Debug model

### Atelier-D20

| Item                 |      Value |
| -------------------- | ---------: |
| Layers               |          8 |
| (d_{\rm model})      |        384 |
| Q heads              |          6 |
| KV heads             |          2 |
| Head dim             |         64 |
| Context              |        512 |
| Vocabulary           |     16,000 |
| FFN                  |      1,024 |
| Experts              |          0 |
| Parameters           | **18.73M** |
| FP32 Adam persistent |   ~0.30 GB |

Use it for:

* unit tests,
* exact CPU↔MPS comparisons,
* routing ablations,
* overfitting tests.

---

## 8.2 Primary 50M baseline

### Atelier-D50

| Item                 |       Value |
| -------------------- | ----------: |
| Layers               |          12 |
| Width                |         512 |
| Q heads              |           8 |
| KV heads             |           2 |
| Context              |   **1,024** |
| Vocabulary           |      24,000 |
| FFN                  |       1,536 |
| Parameters           | **48.464M** |
| FP32 Adam persistent | **0.78 GB** |

This is my recommended **first serious model**.

It is large enough that differences in routing should be measurable while still cheap enough for repeated runs.

---

## 8.3 Serious ~100M baseline

### Atelier-D100

| Item                 |       Value |
| -------------------- | ----------: |
| Layers               |          20 |
| Width                |         640 |
| Q heads              |          10 |
| KV heads             |           2 |
| Context              |       1,024 |
| Vocabulary           |      24,000 |
| FFN                  |       1,664 |
| Parameters           | **98.918M** |
| FP32 Adam persistent | **1.58 GB** |

Use this after the 50M architecture has stabilized.

---

## 8.4 Total-parameter dense control

### Atelier-D133

| Item       |        Value |
| ---------- | -----------: |
| Layers     |           20 |
| Width      |          768 |
| Q heads    |           12 |
| KV heads   |            3 |
| Vocabulary |          24k |
| FFN        |        1,856 |
| Parameters | **133.448M** |

This model exists specifically to total-parameter-match the MoE below.

---

## 8.5 First scientifically clean MoE

### Atelier-M133

Same backbone as D50:

| Item                 |        Value |
| -------------------- | -----------: |
| Layers               |           12 |
| Width                |          512 |
| Q/KV heads           |        8 / 2 |
| Context              |        1,024 |
| Vocabulary           |          24k |
| Expert FFN           |        1,536 |
| Experts              |        **4** |
| Active experts       |        **1** |
| Total params         | **133.423M** |
| Rough active params  |  **48.488M** |
| FP32 Adam persistent |  **2.13 GB** |

This is the most important configuration in the report.

[
133.423M \approx 133.448M
]

versus D133,

while

[
48.488M \approx 48.464M
]

versus D50.

That gives almost perfect experimental matching.

---

## 8.6 Medium MoE

### Atelier-M162

| Item                 |       Value |
| -------------------- | ----------: |
| Layers               |          12 |
| Width                |         576 |
| Q/KV heads           |       9 / 3 |
| FFN/expert           |       1,664 |
| Experts              |           4 |
| Top-k                |           1 |
| Total                | **162.49M** |
| Active               |  **58.97M** |
| FP32 Adam persistent |    ~2.60 GB |

---

## 8.7 Final-scale MoE

### Atelier-M251

| Item                 |          Value |
| -------------------- | -------------: |
| Layers               |             16 |
| Width                |            640 |
| Q/KV heads           |         10 / 2 |
| Context              | 1024 initially |
| Vocabulary           |            24k |
| Expert FFN           |          1,792 |
| Experts              |              4 |
| Active               |              1 |
| Total params         |    **251.33M** |
| Active params        |     **86.18M** |
| FP32 Adam persistent |       ~4.02 GB |

This is close to the upper end I would actually train for a paper.

---

# 9. Training plan with hard exit criteria

## Stage 0 — mathematical/reference implementation

Implement manually:

* tokenizer interface,
* embedding,
* RMSNorm,
* RoPE,
* causal attention,
* GQA,
* SwiGLU,
* Transformer block,
* cross entropy,
* optimizer wrapper,
* checkpointing.

### Exit criteria

CPU and MPS forward outputs agree within dtype-appropriate tolerances.

Gradients agree.

Save→load reproduces outputs.

Resume training reproduces the same next-step loss.

No CPU fallback in benchmark configuration.

**Do not proceed otherwise.**

---

## Stage 1 — single-batch overfit

Use D20.

Train on 1–4 sequences repeatedly.

### Exit

Training CE should become extremely small; target roughly

[
L<0.05
]

if the corpus construction makes complete memorization possible.

Generated sequences reproduce training samples.

No unexplained gradient explosion.

---

## Stage 2 — tiny corpus

Use perhaps 10–50M tokens.

TinyStories is suitable for this *pipeline validation* because it was explicitly created to permit coherent training of very small models. It is not the final general-purpose corpus. ([[arXiv](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com)][28])

### Exit

* train loss decreases;
* validation loss initially decreases;
* no unexplained divergence;
* checkpoint resume works;
* generation transitions from noise to structured text;
* throughput stable;
* memory stable over thousands of steps.

---

## Stage 3 — tokenizer experiment

Compare:

* 16k BPE,
* 24k BPE,
* perhaps 32k BPE.

Same text **bytes**, not same number of tokens.

Evaluate:

* BPB,
* compression ratio,
* tokens/s,
* vocabulary-projection FLOPs,
* generation.

### Exit

Freeze one tokenizer before architecture comparisons.

My default expectation is **24k**, but the benchmark should decide.

---

## Stage 4 — D50 baseline

Use a fixed sample from a general English corpus.

FineWeb provides a large, documented Common-Crawl-derived English corpus; Dolma provides a documented mixture including web, scientific material, code, books and encyclopedic text. ([[arXiv](https://arxiv.org/abs/2406.17557?utm_source=chatgpt.com)][29])

For maximum experimental cleanliness I would initially use **one fixed FineWeb subset** rather than constantly changing corpus mixtures.

### Pilot budget

~500M tokens.

Then potentially ~1B.

### Exit

* stable validation curve,
* no loss spikes,
* no memory drift,
* throughput within ~15% of calibrated expectation,
* generation evaluation working,
* repeat metrics working.

---

## Stage 5 — architecture ablations

One variable at a time.

For example:

1. LayerNorm → RMSNorm
2. GELU → SwiGLU
3. learned position → RoPE
4. MHA → GQA

Do not run a giant factorial campaign.

### Exit

Only retain changes that have either:

* repeatable quality benefit,
* meaningful performance benefit,
* or important simplicity advantages.

Freeze the baseline.

---

## Stage 6 — MoE correctness

Implement E=4, top-1 first on D20-sized networks.

Tests should include:

### E=1 equivalence

One expert must reduce exactly to the corresponding dense FFN.

### Forced routing

Forcing every token to expert (j) must equal directly applying expert (j).

### Dispatch permutation

Packed dispatch followed by inverse permutation must preserve token order exactly.

### Gradients

Only executed expert paths should receive the corresponding token gradients.

### Exit

At scale:

* zero token dropping,
* no permanently dead experts,
* acceptable load CV,
* all router metrics logged,
* no NaNs,
* preferably ≥60–70% of D50's throughput at comparable active work.

If performance is below that threshold, **stop and optimize dispatch before training larger models.**

---

## Stage 7 — conventional M133

Train D50 and standard M133 on identical token order.

This is the experiment that establishes whether sparse capacity itself helps.

### Exit

Determine:

[
\Delta BPB_{\rm sparse}
]

and actual throughput penalty.

If conventional MoE is strictly worse in loss *and* wall time, do not assume a more complex router will rescue it automatically.

---

## Stage 8 — stability analysis before stability routing

Before putting the signal into the router, test:

[
\operatorname{corr}
\left(
r_\ell,,
-\log p(x_{t+1})
\right).
]

Also condition on:

* token frequency,
* sequence position,
* punctuation,
* token length,
* current router entropy.

### Exit

The candidate signal must demonstrate **independent predictive information about token difficulty**.

If it does not, reject or revise the hypothesis.

This stage is essential.

---

## Stage 9 — M133 stability router

Now compare:

[
D50
,\quad
D133
,\quad
M133_{\rm standard}
,\quad
M133_{\rm stability}.
]

Run multiple seeds at an affordable budget before committing to final scale.

### Exit

Require at least:

* consistent BPB direction across ≥2 seeds,
* no expert collapse,
* repeat-rate improvement not attributable to decoding,
* insignificant extra active FLOPs,
* mechanistic evidence that stability information altered useful routes.

---

## Stage 10 — final experiment

Only now move to:

* D100,
* M162 or M251,
* 1–2B+ tokens,
* preferably 3 seeds where economically possible.

The 250M run should be confirmatory, not exploratory.

---

# 10. Apple-optimized implementation guidance

## PyTorch reference training loop

Keep it boring:

```text
token batch
  ↓
single MPS transfer
  ↓
forward
  ↓
loss
  ↓
backward
  ↓
optional gradient clip
  ↓
AdamW
```

No abstractions that conceal device movement.

---

## Tensor layout

Prefer:

```text
[B, T, D]
```

at the model API.

Flatten only where appropriate:

```text
[N, D], N=B×T
```

for:

* FFN,
* router,
* MoE dispatch.

Keep expert weights contiguous.

---

## Recommended MoE dispatch

Do **not** do:

```python
for token in tokens:
    experts[id](token)
```

Instead:

```text
[B,T,D]
   ↓ flatten
[N,D]
   ↓ router
[N,E]
   ↓ argmax
expert_id[N]
   ↓ argsort expert_id
packed[N,D]
   ↓
4 contiguous expert segments
   ↓
expert GEMMs
   ↓
inverse permutation
   ↓
[N,D]
```

For only four experts, a Python loop across **experts**, rather than tokens, is acceptable for the first implementation.

Later investigate grouped/segmented GEMM.

MLX's `segmented_mm` makes this particularly relevant as a future optimization experiment. ([[ML Explore](https://ml-explore.github.io/mlx/build/html/python/ops.html?utm_source=chatgpt.com)][15])

---

## Static-capacity benchmark

Implement a second dispatch mode:

```text
[E,C,D]
```

with fixed capacity (C).

Then benchmark:

* dynamic packed,
* fixed padded,
* bucketed padded.

This could itself produce a useful Apple-specific engineering result.

---

## Precision protocol

Do:

1. FP32 reference.
2. lower-precision forward/backward benchmark.
3. numerical comparison on same minibatches.
4. router/logits in FP32 if needed.
5. long-run stability test.

Never select a precision only because it benchmarks faster for 50 steps.

---

## Memory instrumentation

At every evaluation interval log:

```python
torch.mps.current_allocated_memory()
torch.mps.driver_allocated_memory()
torch.mps.recommended_max_memory()
```

These interfaces distinguish tensor memory, Metal-driver allocations and recommended working-set size. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/generated/torch.mps.driver_allocated_memory.html?utm_source=chatgpt.com)][6])

---

## Profiling

Use three levels:

### Lightweight

tokens/s and step-time quantiles.

### PyTorch profiler

Find CPU/MPS operator bottlenecks. PyTorch provides `torch.profiler` as its integrated performance profiler. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/profiler.html?utm_source=chatgpt.com)][30])

### Metal/Instruments

MPS signposts and Metal capture for suspicious sections. ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/generated/torch.mps.profiler.start.html?utm_source=chatgpt.com)][31])

Profile MoE separately from the Transformer.

---

## Reproducibility manifest

Every run should produce something like:

```yaml
git_commit:
dirty_tree:
python:
torch:
macos:
machine:
device:
dtype:

model:
  layers:
  d_model:
  heads:
  kv_heads:
  ffn:
  experts:
  top_k:

tokenizer_sha256:
dataset_manifest_sha256:

seed:
data_seed:
init_seed:

optimizer:
schedule:

tokens_seen:
wall_seconds:
tokens_per_second:
peak_tensor_memory:
peak_driver_memory:
```

Keep only manifests and small summaries in Git.

Datasets/checkpoints/logs belong under external paths such as:

```text
~/atelier_data/
~/atelier_checkpoints/
~/atelier_runs/
```

with paths configurable through environment/config files.

---

# 11. Risk register

| Risk                      | Early diagnostic                                        | Mitigation                                                       |
| ------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- |
| **Insufficient data**     | repeated epochs; validation plateaus                    | fixed 1–3B+ token corpus subset                                  |
| **Overfitting**           | widening train/val gap                                  | more data, smaller model, regularization                         |
| **Repetition**            | repeat-4 rises despite good CE                          | fixed decoding evaluation; inspect data duplicates               |
| **Poor MPS performance**  | low utilization; many tiny kernels                      | vectorized routing, fixed shapes, MLX comparison                 |
| **Expert collapse**       | high load CV/Gini, dead experts                         | balancing loss, router LR, initialization, temperature           |
| **Instability**           | router-logit growth, loss spikes, NaNs                  | z-loss-style stabilization, clipping, FP32 router                |
| **Misleading comparison** | models see different text or tuning                     | frozen data order and equal tuning budget                        |
| **Memory exhaustion**     | driver allocation approaches working-set recommendation | lower microbatch, then checkpointing                             |
| **Training too slow**     | pilot extrapolation exceeds budget                      | terminate before final scale; don't “hope” it improves           |
| **Weak novelty**          | overlap found with difficulty/entropy routing           | focus on dynamical signal + mechanism + matched-compute evidence |
| **Fake specialization**   | routes differ but representations do not                | spectral/semantic controls                                       |
| **Decoding confound**     | repetition disappears with sampler changes              | report architecture across multiple identical decoding policies  |

One less obvious risk deserves emphasis:

### Routing complexity without quality relevance

A very recent controlled study at roughly 76–84M parameters reported that several routing topologies converged to very similar language-modeling quality, suggesting that sophisticated routing structures may matter much less than often assumed. ([[arXiv](https://arxiv.org/abs/2604.14419?utm_source=chatgpt.com)][32])

That should make the project **more rigorous**, not less interesting.

Your stability router must beat a deliberately simple router under controlled conditions.

---

# 12. Prioritized reading list

## A. Transformer fundamentals

1. **Vaswani et al. — Attention Is All You Need**
   `https://arxiv.org/abs/1706.03762` ([[arXiv](https://arxiv.org/abs/1706.03762?utm_source=chatgpt.com)][33])

2. **Zhang & Sennrich — Root Mean Square Layer Normalization**
   `https://arxiv.org/abs/1910.07467`

3. **Shazeer — GLU Variants Improve Transformer**
   `https://arxiv.org/abs/2002.05202` ([[arXiv](https://arxiv.org/abs/2002.05202?utm_source=chatgpt.com)][2])

4. **Su et al. — RoFormer / Rotary Position Embedding**
   `https://arxiv.org/abs/2104.09864`

5. **Ainslie et al. — GQA**
   `https://arxiv.org/abs/2305.13245`

---

## B. Optimization and stability

1. **Xiong et al. — On Layer Normalization in the Transformer Architecture**
   `https://arxiv.org/abs/2002.04745`

2. **Bachlechner et al. — ReZero is All You Need**
   `https://arxiv.org/abs/2003.04887`

3. **Wang et al. — DeepNet: Scaling Transformers to 1,000 Layers**
   `https://arxiv.org/abs/2203.00555` ([[arXiv](https://arxiv.org/abs/2203.00555?utm_source=chatgpt.com)][25])

4. **Yang et al. — Tensor Programs V / μTransfer**
   `https://arxiv.org/abs/2203.03466`

5. **Geometric/Dynamical analyses of Transformer stability**
   Include recent order/chaos, signal-propagation and Jacobian work, but treat it as theory/diagnostics rather than an architecture recipe.

---

## C. Scaling laws and data

1. **Kaplan et al. — Scaling Laws for Neural Language Models**
   `https://arxiv.org/abs/2001.08361`

2. **Hoffmann et al. — Training Compute-Optimal Large Language Models**
   `https://arxiv.org/abs/2203.15556` ([[arXiv](https://arxiv.org/abs/2203.15556?utm_source=chatgpt.com)][8])

3. **FineWeb**
   `https://arxiv.org/abs/2406.17557` ([[arXiv](https://arxiv.org/abs/2406.17557?utm_source=chatgpt.com)][29])

4. **Dolma**
   `https://arxiv.org/abs/2402.00159` ([[arXiv](https://arxiv.org/abs/2402.00159?utm_source=chatgpt.com)][34])

5. **TinyStories** — for development-scale experiments, not final general modeling
   `https://arxiv.org/abs/2305.07759` ([[arXiv](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com)][28])

---

## D. MoE — read these particularly carefully

### Foundations

1. **Shazeer et al. — Outrageously Large Neural Networks: The Sparsely-Gated MoE Layer**
   `https://arxiv.org/abs/1701.06538`

2. **GShard**
   `https://arxiv.org/abs/2006.16668` ([[arXiv](https://arxiv.org/abs/2006.16668?utm_source=chatgpt.com)][16])

3. **Switch Transformer**
   `https://arxiv.org/abs/2101.03961` ([[arXiv](https://arxiv.org/abs/2101.03961?utm_source=chatgpt.com)][3])

### Routing/stability

4. **ST-MoE**
   `https://arxiv.org/abs/2202.08906` ([[arXiv](https://arxiv.org/abs/2202.08906?utm_source=chatgpt.com)][18])

5. **Expert Choice Routing**
   `https://arxiv.org/abs/2202.09368`

6. **StableMoE**
   `https://arxiv.org/abs/2204.08396`

### Modern systems

7. **Mixtral of Experts**
   `https://arxiv.org/abs/2401.04088`

8. **DeepSeekMoE**
   `https://arxiv.org/abs/2401.06066` ([[arXiv](https://arxiv.org/abs/2401.06066?utm_source=chatgpt.com)][17])

9. **OLMoE**
   `https://arxiv.org/abs/2409.02060` ([[arXiv](https://arxiv.org/abs/2409.02060?utm_source=chatgpt.com)][21])

---

## E. Conditional/difficulty-aware computation

1. **Mixture-of-Depths**
   `https://arxiv.org/abs/2404.02258` ([[arXiv](https://arxiv.org/abs/2404.02258?utm_source=chatgpt.com)][4])

2. **DynaMoE — token-difficulty-driven MoEfication**
   `https://arxiv.org/abs/2502.12325` ([[arXiv](https://arxiv.org/abs/2502.12325?utm_source=chatgpt.com)][26])

3. **DynaMoE — dynamic token-level expert activation**
   `https://arxiv.org/abs/2603.01697` ([[arXiv](https://arxiv.org/abs/2603.01697?utm_source=chatgpt.com)][35])

4. **When Are Experts Misrouted?**
   `https://arxiv.org/abs/2605.07260` ([[arXiv](https://arxiv.org/abs/2605.07260?utm_source=chatgpt.com)][36])

5. **GeMoE**
   `https://arxiv.org/abs/2606.26287` ([[arXiv](https://arxiv.org/abs/2606.26287?utm_source=chatgpt.com)][37])

6. **EntropyMoE**
   `https://arxiv.org/abs/2608.06398` ([[arXiv](https://arxiv.org/abs/2608.06398?utm_source=chatgpt.com)][19])

The last item is especially relevant because it appeared only recently relative to this assessment and further reduces the novelty of generic entropy/difficulty routing.

---

## F. Apple Silicon

### PyTorch

* MPS backend
  `https://docs.pytorch.org/docs/stable/notes/mps.html` ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/notes/mps.html?utm_source=chatgpt.com)][1])
* MPS API
  `https://docs.pytorch.org/docs/stable/mps.html` ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/mps.html?utm_source=chatgpt.com)][38])
* MPS environment variables
  `https://docs.pytorch.org/docs/stable/mps_environment_variables.html` ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/mps_environment_variables.html?utm_source=chatgpt.com)][11])
* PyTorch 2.13 release / Apple MPS changes
  `https://pytorch.org/blog/pytorch-2-13-release-blog/` ([[PyTorch](https://pytorch.org/blog/pytorch-2-13-release-blog/?utm_source=chatgpt.com)][9])
* Activation checkpointing
  `https://docs.pytorch.org/docs/stable/checkpoint.html` ([[PyTorch Documentation](https://docs.pytorch.org/docs/stable/checkpoint.html?utm_source=chatgpt.com)][7])

### MLX

* MLX documentation
  `https://ml-explore.github.io/mlx/` ([[ML Explore](https://ml-explore.github.io/mlx/?utm_source=chatgpt.com)][39])
* Unified memory
  `https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html` ([[ML Explore](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html?utm_source=chatgpt.com)][10])
* Compilation
  `https://ml-explore.github.io/mlx/build/html/usage/compile.html` ([[ML Explore](https://ml-explore.github.io/mlx/build/html/usage/compile.html?utm_source=chatgpt.com)][14])
* Fast operations
  `https://ml-explore.github.io/mlx/build/html/python/fast.html` ([[ML Explore](https://ml-explore.github.io/mlx/build/html/python/fast.html?utm_source=chatgpt.com)][40])

---

## G. Evaluation and reproducibility

1. **Pythia**
   `https://arxiv.org/abs/2304.01373` ([[arXiv](https://arxiv.org/abs/2304.01373?utm_source=chatgpt.com)][22])

2. **Holtzman et al. — Neural Text Degeneration**
   `https://arxiv.org/abs/1904.09751` ([[arXiv](https://arxiv.org/abs/1904.09751?utm_source=chatgpt.com)][23])

3. **Welleck et al. — Unlikelihood Training**
   `https://arxiv.org/abs/1908.04319` ([[arXiv](https://arxiv.org/abs/1908.04319?utm_source=chatgpt.com)][24])

4. **MAUVE**
   `https://arxiv.org/abs/2102.01454`

For this project, however, **validation BPB + controlled repetition metrics + performance metrics should remain primary**. Do not bury the central experiment beneath dozens of downstream benchmarks.

---

# 13. Final recommendation

## Recommended first model

**Atelier-D50**

* 12 layers
* (d=512)
* 8 Q heads
* 2 KV heads
* SwiGLU 1536
* RMSNorm
* RoPE
* 24k vocabulary
* context 1024
* **48.46M parameters**

D20 should exist as the debugging vehicle, but D50 should be the first model you regard as a research result.

---

## Recommended first experiment

Not MoE.

First establish:

> **Can Atelier-D50 produce a reproducible loss/throughput/repetition baseline on a fixed general-English corpus under PyTorch MPS?**

Train roughly **500M tokens first**.

Only extend toward ~1B after the training curve, resume logic, profiler, memory logging and evaluation suite are trustworthy.

---

## Recommended first MoE

**Atelier-M133**

[
P_{\rm total}=133.423M
]

[
P_{\rm active}\approx48.488M.
]

Use:

* four experts,
* top-1,
* equal-width experts,
* no token dropping,
* simple linear router,
* Switch-style load balancing,
* router-stability regularization,
* packed vectorized dispatch.

It is almost perfectly active-parameter-matched to D50 and total-parameter-matched to D133.

That experimental geometry is too useful to give up for a more complicated architecture.

---

## Recommended research thesis

The central experiment should ultimately become:

[
\boxed{
D50
\quad vs\quad
D133
\quad vs\quad
M133_{\rm standard}
\quad vs\quad
M133_{\rm stability}
}
]

with identical text, tokenizer, token order and training budget.

The hypothesis:

> **A cheap dynamical signal derived from relative residual change identifies tokens for which conventional routing is weak, and incorporating that signal into top-1 expert selection improves language-modeling efficiency and reduces degeneration without increasing executed expert compute.**

The strongest paper would not merely report that M133-S wins.

It would establish:

1. residual dynamics predict token difficulty;
2. conventional routers mishandle some of those tokens;
3. the modified router changes their routes;
4. those changed routes reduce conditional loss;
5. the effect survives matched-token and matched-active-FLOP comparisons;
6. expert utilization remains stable;
7. the result appears at more than one scale;
8. MPS overhead is small enough that the algorithm remains locally useful.

Recent counterfactual-routing results make point 2 particularly plausible, but do not establish your proposed mechanism. ([[arXiv](https://arxiv.org/abs/2605.07260?utm_source=chatgpt.com)][36])

---

## What I would **not** attempt yet

Do not begin with:

* 1B pretraining;
* 8–64 experts;
* top-2 routing;
* heterogeneous expert sizes;
* shared experts;
* expert choice;
* variable (k);
* Mixture-of-Depths;
* reversible Transformers;
* 4096+ context;
* custom Metal kernels;
* quantized training;
* multi-corpus mixtures;
* downstream instruction tuning;
* RLHF;
* sophisticated energy-based objectives.

Each can be scientifically interesting later. Together they make the experiment uninterpretable.

And specifically: **do not make “physics-inspired AI” the headline before the physics gives you a measurable variable and falsifiable prediction.** Residual growth, Jacobian spectra, entropy and phase behavior qualify. Metaphors do not.

---

# What would count as a successful project?

There are three levels.

### Engineering success

You have a clean from-scratch LM stack on MPS that:

* trains 20–250M models,
* reproduces runs,
* profiles memory/throughput,
* implements efficient sparse dispatch,
* has a second MLX backend or benchmark,
* stores all experiment provenance.

That alone is a substantial educational system.

### Scientific success

At matched active compute:

[
M133_{\rm standard}
<
D50
]

in validation BPB with tolerable wall-clock overhead, and the effect survives multiple seeds.

That demonstrates useful sparse capacity at genuinely local scale.

### Strong research success

The proposed stability router then produces something like:

[
BPB(M133_S)
<
BPB(M133)
<
BPB(D50)
]

while also producing:

[
R_4(M133_S)
<
R_4(M133)
]

under identical decoding, with no increase in active expert count and with a mechanistic relationship between residual dynamics, token difficulty and beneficial route changes.

Even a **small but reproducible** improvement would be more scientifically valuable than training a 1B model once.

A result showing that the stability router does **not** improve asymptotic LM quality, despite strongly predicting token difficulty, could also be publishable if the analysis convincingly explains why. Recent evidence that sophisticated routing topology can have surprisingly little effect makes a well-controlled negative result scientifically credible rather than a project failure. ([[arXiv](https://arxiv.org/abs/2604.14419?utm_source=chatgpt.com)][32])

**I would therefore make Atelier-M133, not a 300M or 1B dense model, the architectural centerpiece of The Atelier Lab.** The D50/D133/M133 matched triangle gives the project an unusually clean foundation for answering the actual research question rather than simply demonstrating that sparse training runs on a Mac.

[1]: https://docs.pytorch.org/docs/stable/notes/mps.html?utm_source=chatgpt.com "MPS backend — PyTorch 2.13 documentation"
[2]: https://arxiv.org/abs/2002.05202?utm_source=chatgpt.com "GLU Variants Improve Transformer"
[3]: https://arxiv.org/abs/2101.03961?utm_source=chatgpt.com "Switch Transformers: Scaling to Trillion Parameter Models with Simple and Efficient Sparsity"
[4]: https://arxiv.org/abs/2404.02258?utm_source=chatgpt.com "Mixture-of-Depths: Dynamically allocating compute in transformer-based language models"
[5]: https://docs.pytorch.org/tutorials/intermediate/optimizer_step_in_backward_tutorial.html?utm_source=chatgpt.com "How to save memory by fusing the optimizer step into ..."
[6]: https://docs.pytorch.org/docs/stable/generated/torch.mps.driver_allocated_memory.html?utm_source=chatgpt.com "torch.mps.driver_allocated_memory"
[7]: https://docs.pytorch.org/docs/stable/checkpoint.html?utm_source=chatgpt.com "torch.utils.checkpoint"
[8]: https://arxiv.org/abs/2203.15556?utm_source=chatgpt.com "Training Compute-Optimal Large Language Models"
[9]: https://pytorch.org/blog/pytorch-2-13-release-blog/?utm_source=chatgpt.com "PyTorch 2.13 Release Blog"
[10]: https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html?utm_source=chatgpt.com "Unified Memory — MLX 0.32.0 documentation"
[11]: https://docs.pytorch.org/docs/stable/mps_environment_variables.html?utm_source=chatgpt.com "MPS Environment Variables"
[12]: https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.fast.scaled_dot_product_attention.html?utm_source=chatgpt.com "mlx.core.fast.scaled_dot_product_attention"
[13]: https://docs.pytorch.org/docs/stable/generated/torch.mps.event.Event.html?utm_source=chatgpt.com "Event — PyTorch 2.13 documentation"
[14]: https://ml-explore.github.io/mlx/build/html/usage/compile.html?utm_source=chatgpt.com "Compilation — MLX 0.32.0 documentation"
[15]: https://ml-explore.github.io/mlx/build/html/python/ops.html?utm_source=chatgpt.com "Operations — MLX 0.32.0 documentation"
[16]: https://arxiv.org/abs/2006.16668?utm_source=chatgpt.com "GShard: Scaling Giant Models with Conditional Computation and Automatic Sharding"
[17]: https://arxiv.org/abs/2401.06066?utm_source=chatgpt.com "DeepSeekMoE: Towards Ultimate Expert Specialization in Mixture-of-Experts Language Models"
[18]: https://arxiv.org/abs/2202.08906?utm_source=chatgpt.com "ST-MoE: Designing Stable and Transferable Sparse Expert Models"
[19]: https://arxiv.org/abs/2608.06398?utm_source=chatgpt.com "EntropyMoE: Entropy-Aware Sparse Expert Routing for Tokenizer-Free LLMs"
[20]: https://arxiv.org/abs/2604.09780?utm_source=chatgpt.com "The Myth of Expert Specialization in MoEs: Why Routing Reflects Geometry, Not Necessarily Domain Expertise"
[21]: https://arxiv.org/abs/2409.02060?utm_source=chatgpt.com "OLMoE: Open Mixture-of-Experts Language Models"
[22]: https://arxiv.org/abs/2304.01373?utm_source=chatgpt.com "Pythia: A Suite for Analyzing Large Language Models Across Training and Scaling"
[23]: https://arxiv.org/abs/1904.09751?utm_source=chatgpt.com "The Curious Case of Neural Text Degeneration"
[24]: https://arxiv.org/abs/1908.04319?utm_source=chatgpt.com "Neural Text Generation with Unlikelihood Training"
[25]: https://arxiv.org/abs/2203.00555?utm_source=chatgpt.com "DeepNet: Scaling Transformers to 1,000 Layers"
[26]: https://arxiv.org/abs/2502.12325?utm_source=chatgpt.com "From Dense to Dynamic: Token-Difficulty Driven MoEfication of Pre-Trained LLMs"
[27]: https://arxiv.org/abs/2604.04230?utm_source=chatgpt.com "Three Phases of Expert Routing: How Load Balance Evolves During Mixture-of-Experts Training"
[28]: https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com "TinyStories: How Small Can Language Models Be and Still Speak Coherent English?"
[29]: https://arxiv.org/abs/2406.17557?utm_source=chatgpt.com "The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale"
[30]: https://docs.pytorch.org/docs/stable/profiler.html?utm_source=chatgpt.com "torch.profiler — PyTorch 2.13 documentation"
[31]: https://docs.pytorch.org/docs/stable/generated/torch.mps.profiler.start.html?utm_source=chatgpt.com "torch.mps.profiler.start"
[32]: https://arxiv.org/abs/2604.14419?utm_source=chatgpt.com "Equifinality in Mixture of Experts: Routing Topology Does Not Determine Language Modeling Quality"
[33]: https://arxiv.org/abs/1706.03762?utm_source=chatgpt.com "Attention Is All You Need"
[34]: https://arxiv.org/abs/2402.00159?utm_source=chatgpt.com "Dolma: an Open Corpus of Three Trillion Tokens for Language Model Pretraining Research"
[35]: https://arxiv.org/abs/2603.01697?utm_source=chatgpt.com "DynaMoE: Dynamic Token-Level Expert Activation with ..."
[36]: https://arxiv.org/abs/2605.07260?utm_source=chatgpt.com "When Are Experts Misrouted? Counterfactual Routing Analysis in Mixture-of-Experts Language Models"
[37]: https://arxiv.org/abs/2606.26287?utm_source=chatgpt.com "GeMoE: Gating Entropy is All You Need for Uncertainty ..."
[38]: https://docs.pytorch.org/docs/stable/mps.html?utm_source=chatgpt.com "torch.mps — PyTorch 2.13 documentation"
[39]: https://ml-explore.github.io/mlx/?utm_source=chatgpt.com "MLX 0.32.0 documentation"
[40]: https://ml-explore.github.io/mlx/build/html/python/fast.html?utm_source=chatgpt.com "Fast — MLX 0.32.0 documentation"
