# The Atelier Lab — Roadmap to Frontier AI Expertise

> **Goal:** Become one of the best in the world at the full stack of modern AI —
> LLM training, post-training, deployment, systems, and research — mastering both
> the *engineering* and the *terminology*. This is the living tracking document.
> The Atelier Lab (agent + foundation tracks) is the vehicle; this file is the map.

- **Owner:** Monit
- **Machine:** MacBook Pro M3 Pro · 36 GB unified memory · macOS (single machine, $0, local-first)
- **Started tracking:** 2026-07-07
- **Cadence assumption:** ~10–15 hrs/week (part-time intensive). Adjust dates to your reality.

---

## 0. How to use this file

- Mark tasks: `- [ ]` not started · `- [x]` done · `- [~]` in progress (edit the `~` in yourself).
- Every deliverable should produce a **committed artifact** (code, a written result, a plot, or a doc). Learning that leaves no artifact doesn't count here.
- Prefer **build-from-scratch → then framework**. Understand the primitive before adopting the tool that hides it.
- Log every meaningful session in [§9 Progress Log](#9-progress-log). Terse is fine.
- **Honesty rule:** negative results and hard limits are features. Record where things fail.
- Re-read [§8 Honest limits](#8-honest-limits-of-a-single-laptop) whenever a task feels impossible — some are, and the right move is *read + tiny reproduction*, not brute force.

**Legend for effort tags:** 🟢 hours · 🟡 days · 🔴 week+ · 📖 reading · 🧪 experiment · 🛠️ build · ✍️ write-up

---

## 1. Where you are now (baseline audit)

Honest snapshot as of 2026-07-07. This is an unusually strong starting point — most learners have notebooks; you have measured systems.

**Applied agents (Atelier) — strong / near-complete**
- [x] Hand-built ReAct loop, no framework (`agent/react.py`, `agent/loop.py`)
- [x] Tool registry + MCP server (files, code_exec, test_runner, repo_map, search, shell, ast_edit)
- [x] RAG: ingest → chunk → local bge embeddings → ChromaDB → hybrid (dense + BM25 + RRF) + rerank
- [x] Persistent semantic memory across sessions
- [x] Eval harness: frozen doc-QA / code / combined suites, deterministic metrics + LLM-judge, regression gate
- [x] LoRA difficulty router (Qwen2.5-0.5B, 100% held-out)
- [x] Planner-router trained + honestly evaluated (format learned, routing not — data-limited) *(2026-07-06)*
- [x] One-command reproduction + public writeup

**Foundation (from-scratch models) — early / real**
- [x] nanochat baseline: 73M @ ~18.7k tok/s, 286M @ ~4.5k tok/s (exp 000)
- [x] Sanskrit vs English tokenizer + pretraining pilot (exp 002)
- [x] Data pipeline: SanskritPile builder (clean/dedup/normalize/filter)
- [ ] Foundation exp 001 (20k-step 73M run: undertraining vs capacity) — **designed, not run**
- [ ] From-scratch annotated transformer (`foundation/models/`) — **not started**

**Deployment / systems — the gap (now being closed)**
- [x] Inference benchmark: prefill vs decode, TTFT, memory, prompt-cache trap, param-count≠speed (exp 003) *(2026-07-06)*
- [ ] Quantization / batching / serving-engine depth — **early**

**Post-training / alignment — introductory**
- [x] LoRA/SFT fundamentals (both routers)
- [ ] The alignment ladder (SFT → DPO → GRPO) — **not started**

---

## 2. The eight pillars (skill map)

Expertise = depth across these eight. Check sub-skills as you genuinely *own* them (can explain + implement, not just recognize).

### Pillar 1 — Tokenization & Data
- [x] BPE training, vocab sizing, compression metrics (bytes/token)
- [ ] SentencePiece / Unigram vs BPE trade-offs
- [ ] Byte-level BPE, tokenizer fertility, vocabulary utilization
- [ ] Dedup at scale: exact + MinHash/LSH near-dup
- [ ] Quality filtering: perplexity filter, classifier filter, heuristic rules
- [ ] Data mixing / domain weighting; decontamination against eval sets
- [ ] Tokens-per-parameter budgeting (Chinchilla-optimal data)

### Pillar 2 — Architecture
- [ ] Implement a transformer block from scratch, annotated
- [ ] Attention: MHA → MQA → GQA (implement + measure KV savings)
- [ ] Positional: absolute → learned → RoPE → ALiBi (implement RoPE)
- [ ] Normalization: LayerNorm vs RMSNorm; pre-norm vs post-norm
- [ ] Activations: ReLU → GELU → SwiGLU/GeGLU
- [ ] KV cache mechanics (already measured its cost in exp 003 — now build one)
- [ ] Mixture-of-Experts: router, top-k, load balancing, active vs total params
- [ ] Long-context: sliding-window, attention sinks, RoPE scaling

### Pillar 3 — Pretraining
- [x] Real training runs with throughput + BPB loss (exp 000/002)
- [ ] Optimizers: AdamW internals; Muon; second-order (Shampoo) awareness
- [ ] LR schedules: warmup, cosine, WSD; grad clipping; weight decay
- [ ] Mixed precision: FP32/FP16/BF16/FP8 — what breaks and why
- [ ] Gradient accumulation & checkpointing (memory vs compute)
- [ ] Scaling laws: derive your own exponent locally (Kaplan/Chinchilla)
- [ ] Stability: loss spikes, init, μP / hyperparameter transfer

### Pillar 4 — Post-training & Alignment
- [x] LoRA / QLoRA / PEFT (routers)
- [ ] SFT + chat templates + instruction tuning done end-to-end
- [ ] Reward modeling (train a small RM)
- [ ] RLHF / PPO (conceptual + toy)
- [ ] DPO implemented on a small local model
- [ ] GRPO / RLVR (the DeepSeek-R1 reasoning lineage)
- [ ] Distillation; rejection sampling; preference-data construction

### Pillar 5 — Inference & Deployment
- [x] Prefill vs decode, TTFT, memory-bandwidth-bound decode (exp 003)
- [x] Prompt / prefix caching (discovered + measured in exp 003)
- [ ] Quantization deep: GGUF/AWQ/GPTQ, int4/int8/FP8 — accuracy vs speed
- [ ] Continuous/dynamic batching; throughput vs latency curves
- [ ] PagedAttention / vLLM; SGLang; TGI — run one, profile it
- [ ] Speculative decoding (implement a toy draft-model version)
- [ ] Structured / constrained decoding (JSON, grammars)
- [ ] Serving a model behind an API with real load

### Pillar 6 — Agents & Applied Systems *(your strength)*
- [x] ReAct, tool calling, MCP
- [x] RAG (hybrid retrieval + rerank), memory, eval harness
- [ ] Multi-agent orchestration (planner-executor, sub-agents)
- [ ] Advanced retrieval: query rewriting, HyDE, multi-hop
- [ ] Multi-file / repo-scale build-mode tasks
- [ ] Guardrails; prompt-injection defense

### Pillar 7 — Evaluation & Reliability *(your strength)*
- [x] Frozen suites, deterministic metrics, LLM-judge, regression gate
- [ ] Statistical rigor: confidence intervals on small suites, significance
- [ ] Benchmark science: MMLU/GSM8K/HumanEval/SWE-bench formats
- [ ] Contamination / decontamination methodology
- [ ] LLM-judge bias, calibration, inter-rater agreement
- [ ] Groundedness / faithfulness scoring for RAG

### Pillar 8 — Systems & Hardware
- [x] Intuition for the 36 GB budget, MPS throughput, serialize train/serve
- [ ] Roofline: arithmetic intensity, memory-bound vs compute-bound (start: exp 003)
- [ ] FlashAttention: *why* it's faster (IO-awareness), read + understand
- [ ] Read/modify one Metal or Triton kernel
- [ ] Distributed training: DDP, FSDP, ZeRO, tensor/pipeline/data parallelism (read + toy)
- [ ] Profiling a training run; MFU (model FLOPs utilization)

---

## 3. Phased timeline

Five phases over ~12 months, then an open-ended frontier phase. Each phase has a **theme**, **deliverables (checkboxes)**, and an **exit bar**. Dates are targets — move them, don't skip the exit bars.

### 🚩 Phase A — Close loops + Deployment mastery (Jul–Aug 2026)
*Theme: finish what's started; turn the deployment gap into a strength.*

- [x] Train + evaluate the planner-router (honest result recorded) 🟢🧪 *(done 2026-07-06)*
- [x] Inference benchmark v1: prefill/decode/TTFT/memory, 3 models (exp 003) 🟡🧪 *(done 2026-07-06)*
- [ ] Run **Foundation exp 001** (20k-step 73M; undertraining vs capacity) 🔴🧪
- [ ] Write up exp 001: does repetition break with more training? plot loss + samples ✍️
- [ ] Diagnose the "test that didn't work" commit; record the failure honestly ✍️
- [ ] Inference benchmark v2: quantization sweep (same model @ Q2/Q4/Q8) — accuracy vs speed 🟡🧪
- [ ] Stand up **vLLM** (CPU or MPS) and reproduce a throughput-vs-batch-size curve 🟡🛠️
- [ ] 📖 Read: "Attention Is All You Need" (Vaswani 2017); the Illustrated Transformer
- **Exit bar:** exp 001 concluded with a written finding; you can explain, with your own numbers, why decode is memory-bound and how batching/quantization move the throughput-latency curve.

### 🚩 Phase B — Architecture depth + Pretraining science (Sep–Nov 2026)
*Theme: build the model from first principles; make pretraining a controlled science.*

- [ ] Build annotated transformer from scratch in `foundation/models/` (train tiny, overfit a batch first) 🔴🛠️
- [ ] Ablation study: swap in RoPE, RMSNorm, SwiGLU, GQA one at a time; measure Δloss/Δspeed on 73M 🔴🧪✍️
- [ ] Implement a KV cache in your own inference path; measure the speedup 🟡🛠️
- [ ] **Mini scaling-law study:** train 4 sizes (e.g. 20M/73M/150M/286M) matched tokens; fit loss-vs-params; report your local exponent 🔴🧪✍️
- [ ] Tokenizer deep dive: BPE vs Unigram on your corpora; fertility + utilization report 🟡🧪
- [ ] Productionize SanskritPile: dedup (MinHash) + perplexity filter + a data-quality dashboard 🔴🛠️
- [ ] 📖 Read + note: GPT-2/GPT-3 papers, Chinchilla (Hoffmann 2022), RoPE (Su 2021), GQA (Ainslie 2023)
- [ ] 🔁 Reproduce a fragment: RoPE from the paper, matching a reference implementation's outputs
- **Exit bar:** a from-scratch transformer you fully understand; an ablation table with your own deltas; a scaling-law plot with your fitted exponent.

### 🚩 Phase C — Post-training & the Alignment ladder (Dec 2026–Feb 2027)
*Theme: turn a base model into an aligned/reasoning one — the most career-relevant skill right now.*

- [ ] SFT a small base model (0.5–4B) on an instruction set via MLX; chat template correct 🟡🛠️
- [ ] Train a small **reward model** on preference pairs 🟡🛠️
- [ ] Implement **DPO** on a small model; compare to SFT-only on a held-out preference eval 🔴🧪✍️
- [ ] Implement **GRPO** on a verifiable task (e.g. arithmetic/code) — RL with verifiable rewards 🔴🧪✍️
- [ ] Rebuild the planner-router with 10× data + closed label set; re-measure route accuracy (closes the 2026-07-06 finding) 🟡🧪
- [ ] 📖 Read + note: InstructGPT (Ouyang 2022), DPO (Rafailov 2023), DeepSeek-R1 (2025), Constitutional AI
- [ ] ✍️ Write-up: "SFT vs DPO vs GRPO on a laptop — what moved, what didn't"
- **Exit bar:** you have personally run each rung of the ladder once, with a measured before/after, and can explain the reward-model → PPO → DPO → GRPO progression from memory.

### 🚩 Phase D — Systems, efficiency & frontier architectures (Mar–May 2027)
*Theme: the senior layer — kernels, quantization, parallelism, MoE.*

- [ ] FlashAttention: read the paper; write a note explaining the IO/tiling argument; benchmark with vs without where available 🟡📖✍️
- [ ] Read + modify one Metal (MLX) or Triton kernel; measure the change 🔴🛠️
- [ ] Quantization deep: implement/inspect a GPTQ or AWQ path; accuracy-vs-bits curve 🔴🧪
- [ ] Speculative decoding: toy draft+verify with a 0.5B drafting for a 14B; measure acceptance rate 🔴🛠️🧪
- [ ] Distributed training: read Megatron-LM + ZeRO/FSDP; implement a *toy* sharding of a tiny model's optimizer state to internalize ZeRO stages 🔴📖🛠️
- [ ] Build a small **MoE** layer; measure active-vs-total params and the routing behavior 🔴🛠️🧪
- [ ] 📖 Read + note: FlashAttention (Dao 2022), Megatron-LM, ZeRO, Switch Transformer / Mixtral, Speculative Decoding (Leviathan 2023)
- **Exit bar:** you can whiteboard FSDP/ZeRO and FlashAttention from memory, and you've measured a real efficiency technique (quantization or spec-decoding) end-to-end.

### 🚩 Phase E — Capstone: research contribution & release (Jun 2027+)
*Theme: produce something the field notices. Rigor + openness, not flash.*

- [ ] Pick ONE original question within reach on a laptop (candidates in [§6](#6-candidate-research-directions)) 🔴
- [ ] Full literature review of that question ✍️
- [ ] Reproduce one *recent* (last-12-months) paper end-to-end at small scale 🔴🧪
- [ ] Run your controlled experiment with error bars + honest failure analysis 🔴🧪✍️
- [ ] Publish: strong technical blog post or workshop-paper submission ✍️
- [ ] Make ≥1 real open-source contribution (MLX, vLLM, llama.cpp, an eval harness) 🛠️
- **Exit bar:** a published, reproducible result with open artifacts that a stranger can rerun — plus an accepted OSS contribution.

---

## 4. Reading & reproduction track (continuous, all phases)

**Rhythm:** 1–2 papers/week (read + a 5-line note in [§9]), and reproduce a fragment of one paper/month. Reproduction is the single biggest expertise multiplier.

**Foundational canon (read these first, in order):**
- [ ] Attention Is All You Need (2017)
- [ ] GPT-2 (2019) & GPT-3 (2020)
- [ ] Chinchilla — Training Compute-Optimal LLMs (2022)
- [ ] LoRA (2021) · QLoRA (2023)
- [ ] RoPE (2021) · GQA (2023) · FlashAttention (2022)

**Post-training & reasoning:**
- [ ] InstructGPT / RLHF (2022) · DPO (2023) · Constitutional AI (2022)
- [ ] DeepSeek-R1 & GRPO (2025) · reasoning-model literature

**Systems & efficiency:**
- [ ] Megatron-LM · ZeRO · FSDP · Switch Transformer / Mixtral (MoE)
- [ ] Speculative Decoding (2023) · PagedAttention / vLLM (2023) · GPTQ / AWQ

**Data & eval:**
- [ ] The Pile / RefinedWeb / FineWeb (data curation)
- [ ] HELM · SWE-bench · MT-Bench / LLM-as-judge · contamination studies

**Monthly reproduction targets (pick one each month):** RoPE · a KV cache · DPO loss · a GQA layer · a MinHash deduper · a GPTQ quantizer · a speculative-decoding loop.

---

## 5. Terminology mastery (checklist — you should be able to *explain each from memory*)

Tick when you can define it precisely and say why it matters.

**Data/tokenization:** BPE · SentencePiece/Unigram · byte-level BPE · fertility · vocab utilization · MinHash/LSH · perplexity filter · decontamination · tokens-per-parameter
- [ ] all of the above

**Architecture:** self/multi-head attention · causal mask · KV cache · RoPE · ALiBi · GQA/MQA · RMSNorm · pre/post-norm · residual stream · SwiGLU · MoE/router/top-k · sliding-window attention · attention sink
- [ ] all of the above

**Pretraining:** AdamW · Muon · warmup/cosine/WSD · grad clipping · BF16/FP8 mixed precision · gradient accumulation/checkpointing · scaling laws · compute-optimal · BPB/perplexity · μP · loss spike
- [ ] all of the above

**Post-training:** SFT · chat template · LoRA/QLoRA/PEFT · RLHF · reward model · PPO · DPO · GRPO · RLVR · distillation · rejection sampling · alignment tax
- [ ] all of the above

**Inference/deploy:** prefill vs decode · TTFT · inter-token latency · KV cache · continuous batching · PagedAttention · prefix caching · speculative decoding · GGUF/AWQ/GPTQ · int4/FP8 · constrained decoding · throughput vs latency
- [ ] all of the above

**Systems:** memory-bandwidth vs compute bound · arithmetic intensity/roofline · MFU · FlashAttention (IO-aware) · kernel fusion · DDP/FSDP/ZeRO · tensor/pipeline/data parallelism · NCCL · activation checkpointing
- [ ] all of the above

**Agents/eval:** ReAct · tool/function calling · MCP · RAG · chunking · hybrid retrieval · RRF · reranking · HyDE · groundedness · pass@k · contamination · LLM-as-judge · calibration · regression testing
- [ ] all of the above

---

## 6. Candidate research directions (for Phase E)

All laptop-feasible, all measurable, all local-first. Pick one when you get there.

- [ ] **Local-first reliability study** of a dual-mode agent (extend Atelier's eval into a proper paper with error bars + difficulty curves).
- [ ] **Tool-interface design vs model size:** quantify how much reliability comes from better tools vs bigger models (your `ast_edit`/`repo_map` findings are the seed).
- [ ] **Small-model routing:** when does a fine-tuned router actually save compute without hurting success? (the planner-router thread, done rigorously).
- [ ] **Apple-Silicon scaling behavior:** how does training efficiency (MFU, tok/s) scale with model size on MPS vs the CUDA literature?
- [ ] **Script/language efficiency in pretraining:** extend the Sanskrit-vs-English study with matched tokenizers and controlled confounds.
- [ ] **Structural-edit reliability:** why local models fail multi-line code edits and which tool designs fix it.

---

## 7. Portfolio / proof-of-expertise (what you can point to)

Expertise is credible when it's *visible*. Aim to accumulate:
- [ ] The Atelier agent — released, evaluated, reproducible ✅ (largely done — polish + publish)
- [ ] A from-scratch, annotated transformer + training stack
- [ ] A scaling-law plot with your own fitted exponent on Apple Silicon
- [ ] An alignment-ladder write-up (SFT/DPO/GRPO, measured)
- [ ] The inference-benchmark series (deployment depth) — started (exp 003)
- [ ] One published post/paper + one merged OSS PR
- [ ] A public terminology-fluent write-up per pillar (teaching = mastery)

---

## 8. Honest limits of a single laptop

Don't waste months fighting these — cover them by **reading + tiny reproductions**, not brute force:
- ❌ Multi-node distributed training → learn by reading Megatron/ZeRO; do a *toy* single-node sharding to internalize the concept.
- ❌ Frontier-scale (70B+) training → out of reach; understand the recipes, don't run them.
- ❌ Production-scale serving (thousands of QPS) → simulate small; understand batching/PagedAttention conceptually + at small scale.
- ❌ Large-scale RLHF → do toy GRPO/DPO; understand the pipeline.
- ✅ What you *can* master hands-on: architecture, small-scale pretraining, scaling-law *shape*, the full alignment ladder at small scale, quantization, inference/serving internals, agents, evaluation, and the systems *concepts* behind all of it.

The bar for "expert" is **precise reasoning + measured small-scale reproductions + published rigor** — not a GPU cluster.

---

## 9. Progress log (append-only)

> Format: `YYYY-MM-DD — what you did — artifact / result`

- 2026-07-06 — Trained + evaluated the planner-router; wrote `evaluate_planner.py`; honest finding (format learned, routing not, data-limited) — `models/router/planner_adapter/`.
- 2026-07-06 — Built inference benchmark (exp 003); found+fixed the prompt-cache measurement trap; three-model sweep showed param-count ≠ decode speed (gemma4:26b faster than qwen3:14b) — `foundation/experiments/003_local_inference_benchmark/`.
- 2026-07-07 — Created this roadmap.
- _next entry here…_

---

## 10. Quick-start (the next three concrete actions)

1. [ ] Launch **Foundation exp 001** when you can leave the laptop ~5 hrs; write up the result.
2. [ ] Inference benchmark v2: quantization sweep (Q2/Q4/Q8 of one model) — accuracy vs speed.
3. [ ] Start the **from-scratch transformer** in `foundation/models/` — overfit a single batch first.

> *Understand everything. Reproduce faithfully. Experiment rigorously. Build openly.*
