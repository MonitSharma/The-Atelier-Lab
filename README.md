<div align="center">

# The Atelier Lab


### Building Foundation Models. Developing AI Agents. Advancing Local AI.

*A long-term open research laboratory dedicated to understanding, reproducing, and advancing modern Artificial Intelligence—entirely from first principles.*

---

**Current Focus**

 Foundation Models •  AI Agents •  Research Reproductions •  Efficient Training •  Apple Silicon •  Local AI

</div>

---

## Vision

The Atelier Lab is an open research laboratory exploring a simple but ambitious question:

> **How far can modern AI be reproduced, understood, and advanced by a single researcher using only consumer hardware?**

Over the last decade, state-of-the-art AI has become increasingly associated with trillion-token datasets, massive GPU clusters, and proprietary infrastructure. While these resources enable frontier-scale models, they often obscure the underlying ideas behind them.

The Atelier Lab takes the opposite approach.

Rather than treating modern AI systems as black boxes, every component is studied, implemented, benchmarked, and documented from first principles.

The objective is not simply to train language models.

The objective is to understand **why** they work, reproduce important advances from the literature, and develop new ideas through careful experimentation.

---

# Mission

The laboratory is built around four long-term goals.

- **Understand** every major component involved in modern AI systems.
- **Reproduce** influential research with clean and reproducible implementations.
- **Improve** existing methods through systematic experimentation.
- **Build** complete local AI systems capable of running on consumer hardware.

Every project inside this repository contributes toward one or more of these goals.

---

# Research Philosophy

The Atelier Lab is guided by several core principles.

## First Principles

Every important algorithm should be understood mathematically before it is optimized.

---

## Reproducibility

Every experiment should be reproducible from code, documentation, and configuration files.

---

## Engineering Excellence

Research code should remain modular, maintainable, and production-quality.

---

## Scientific Evaluation

Every proposed improvement should be supported by controlled experiments rather than anecdotal observations.

---

## Open Research

Knowledge becomes significantly more valuable when it is shared.

Where possible, implementations, benchmarks, documentation, and experimental findings will remain openly available.

---

# Results at a Glance

A selection of measured findings from the lab so far — every number below comes from a committed experiment artifact, run entirely on a single MacBook Pro (M3 Pro, 36 GB) at zero cloud cost.

### Foundation — training from scratch on Apple Silicon

Baseline `nanochat` runs at two scales. Throughput scales almost linearly with parameter count on the MPS backend, and the larger model reaches a lower validation loss at matched steps.

![Foundation scaling: throughput and validation loss vs model size](assets/foundation_scaling.png)

A controlled three-way pretraining pilot shows Devanagari Sanskrit is far more predictable at the byte level than English under matched `nanochat` configurations — a combined effect of language structure and BPE merge behaviour.

![Sanskrit vs English validation loss](assets/sanskrit_vs_english.png)

### Deployment — local inference benchmark

Decode throughput is memory-bandwidth-bound, not parameter-bound: a 26B model can decode **2.4× faster** than a 14B one on the same machine. Param count is not a proxy for speed.

![Local inference decode speed by model](assets/inference_decode_speed.png)

### Agents — the local Atelier agent

A fully local, dual-mode (knowledge + build) agent evaluated on frozen task suites. It saturates retrieval-augmented Q&A and single-line code fixes, while honestly hitting a reasoning ceiling on multi-line structural code edits.

![Agent reliability scorecard](assets/agent_reliability.png)

A 1-minute LoRA fine-tune takes a 0.5B difficulty router from worse-than-chance to perfect in-distribution routing — the "small model as a cheap component" pattern at the smallest possible scale.

![Router fine-tune lift](assets/router_finetune_lift.png)

> Full methodology and honest limitations: [`atelier_agent/docs/WRITEUP.md`](atelier_agent/docs/WRITEUP.md) and the per-experiment reports under [`foundation/experiments/`](foundation/experiments/).

---

# Laboratory Structure

```
The Atelier Lab
│
├── foundation/
│   ├── tokenizers/
│   ├── datasets/
│   ├── models/
│   ├── training/
│   ├── inference/
│   ├── evaluation/
│   └── experiments/
│
├── atelier_agent/
│   ├── atelier/              # CLI, configuration, banner, MCP server
│   ├── agent/                # ReAct loop, brain client, router, memory
│   ├── tools/                # Tool registry and agent tools
│   ├── rag/                  # Ingestion, retrieval, embeddings, answer synthesis
│   ├── eval/                 # Evaluation runners, metrics, and task suites
│   │   ├── tasks_code/
│   │   ├── tasks_combined/
│   │   └── tasks_docqa/
│   ├── models/
│   │   └── router/           # Router datasets, training scripts, adapter artifacts
│   ├── data/                 # Local runtime data: memory, traces, reports, vector store
│   ├── docs/                 # Architecture, testing, eval, and writeup docs
│   ├── scripts/              # Reproduction scripts
│   ├── sample_task/          # Small test target for build-mode demos
│   ├── tests/                # Fast unit tests
│   ├── Makefile
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── Project.md
│   └── README.md
│
├── research/
│   ├── reproductions/
│   ├── original_ideas/
│   └── reports/
│
├── benchmarks/
│
├── datasets/
│
├── docs/
│
├── papers/
│
└── blog/
```

Each module represents an independent research direction while sharing a common philosophy and engineering foundation.

---

# Projects

## Foundation

The Foundation project investigates how modern language models are built from scratch.

Topics include:

- Tokenization
- Dataset preparation
- Transformer architectures
- Attention mechanisms
- Positional embeddings
- Optimization
- Scaling laws
- Efficient training
- Evaluation
- Inference

The long-term objective is to build a complete, transparent, and reproducible foundation-model training stack.

---

## Atelier

Atelier is an autonomous AI agent built on top of the Foundation project.

Rather than focusing on model training, Atelier explores higher-level intelligence through:

- Tool use
- Planning
- Long-term memory
- Retrieval-Augmented Generation (RAG)
- Multi-step reasoning
- Workflow automation
- Local-first AI

Foundation builds the models.

Atelier uses them.

---

## Research

The Research module serves as the laboratory's experimental workspace.

Every reproduction and original investigation is documented with:

- Literature review
- Implementation
- Experimental setup
- Benchmarks
- Analysis
- Discussion

Representative topics include:

- Modern attention mechanisms
- Efficient optimizers
- Reinforcement learning for language models
- Scaling studies
- Apple Silicon optimization
- Efficient inference
- Emerging model architectures

---

## Benchmarks

Every model and experiment should be evaluated using a consistent methodology.

Metrics include:

- Training loss
- Validation loss
- Perplexity
- Throughput
- Memory usage
- Energy consumption
- Tokens per second
- Inference latency
- Benchmark performance

The objective is to make every comparison scientifically meaningful.

---

# Current Roadmap

### Phase I — Foundations

- Learn every component involved in modern LLM training.
- Build an annotated implementation from first principles.
- Understand the mathematics behind every architectural decision.

---

### Phase II — Reproduction

Faithfully reproduce influential techniques from contemporary AI research.

Examples include:

- Rotary Position Embeddings (RoPE)
- FlashAttention
- Grouped Query Attention
- Modern optimizers
- Efficient training methods
- Post-training alignment techniques

---

### Phase III — Experimental Research

Conduct controlled investigations into questions such as:

- Which techniques most improve small language models?
- How does data quality compare with parameter count?
- Which optimizers perform best under limited compute?
- How efficiently can Apple Silicon train modern language models?

---

### Phase IV — Scaling

Progressively scale the complete training pipeline while preserving reproducibility and engineering quality.

The emphasis is understanding scaling behaviour rather than simply increasing parameter count.

---

### Phase V — Local AI Systems

Integrate foundation models into capable autonomous agents featuring:

- Tool use
- Planning
- Memory
- Retrieval
- Multi-agent collaboration
- Reinforcement learning

---

# Hardware Philosophy

The Atelier Lab intentionally embraces hardware constraints.

Current primary development platform:

- Apple MacBook Pro (M3 Pro)
- 36 GB Unified Memory
- Apple Silicon GPU (Metal/MPS)

Rather than viewing limited compute as a disadvantage, the laboratory treats it as a research constraint.

One of the central research questions is:

> **How far can modern AI be pushed using hardware available to independent researchers?**

---

# Long-Term Vision

The Atelier Lab is intended to grow into a comprehensive open research platform for efficient AI.

The long-term ambition is not to compete with industrial laboratories in scale.

Instead, the goal is to demonstrate that careful engineering, rigorous experimentation, and a deep understanding of first principles can enable meaningful contributions to modern AI research—even from a single machine.

---

> *Understand everything. Reproduce faithfully. Experiment rigorously. Build openly.*
