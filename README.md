# The Atelier Lab

The Atelier Lab is a local-first AI research laboratory for learning language models, measuring Apple Silicon systems, and building reliable agents under a fixed 36 GB unified-memory budget.

## Central question

> How much reliable AI capability can a single researcher obtain from local models under fixed memory, latency, privacy, and compute constraints?

## Three tracks

- **Foundations:** tokenization, language modelling, attention, transformers, training, and autoregressive inference.
- **Local AI systems:** Apple Silicon benchmarking, quantization, KV caching, memory, serving, and routing.
- **Reliable agents:** RAG, tools, code modification, verification, memory, routing, and evaluation.

## Verified results

The current expanded Atelier suites record 17/18 knowledge answers, 13/13 code tasks, and 10/10 combined tasks solved. The suites are modest and mostly single-file; see [current results](docs/CURRENT_RESULTS.md) and [limitations](docs/LIMITATIONS.md). The local inference benchmark found that parameter count alone does not predict decode speed.

## Start here

- [Learning path](docs/START_HERE.md)
- [Run the local agent](atelier_agent/README.md)
- [Atelier operator guide](docs/ATELIER_OPERATOR_GUIDE.md)
- [Atelier user guide with worked examples](docs/ATELIER_USER_GUIDE.md)
- [Work with papers and documents](docs/WORKING_WITH_DOCUMENTS.md)
- [Experiment registry](experiments/registry.yaml)
- [Repository map](docs/REPOSITORY_MAP.md)
- [Atelier Workbench plan](docs/ATELIER_WORKBENCH_PLAN.md)

## Quick start

```bash
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
make -C atelier_agent test       # requires the project's .venv
```

The educational `foundation/minillm` package is CPU-friendly and has no dataset download step. The agent remains self-contained under `atelier_agent/`; existing CLI, RAG, tools, evaluation, router, MCP, and reproduction commands are preserved.

## Active phase

The current phase is the operational Atelier workbench: use the local model
stack on real research documents, measure retrieval and answer quality, and
turn the strongest research questions into small, testable experiments. The
foundation and learning tracks remain active but are no longer the only entry
point.

## Phase 2 — Create the four-tier model stack

The Atelier Lab should maintain four capability tiers rather than ten overlapping general-purpose models. Each tier has a distinct job in the orchestration system.

### Tier A — Tiny worker

Target approximately the 2–4B parameter range. LFM2.5-2.6B is an interesting candidate for evaluation.

Primary responsibilities:

- routing and classification
- metadata extraction
- query rewriting
- tool selection
- structured JSON generation
- RAG processing
- cheap, repetitive reasoning

This model is not intended to write research papers. Its job is to decide: **“What needs to happen next?”**

### Tier B — Small coding agent

Target approximately the 7–10B parameter range. Benchmark Ornith-9B or whichever strong agentic coding model is current when the evaluation begins.

Responsibilities:

- small bug fixes
- scripts and tests
- boilerplate
- data manipulation
- simple refactoring
- repository exploration

### Tier C — Main local intelligence

Reserve this position for a Qwen3.8-27B Q4-class quantization when it is ready for adoption.

This is the primary local model for:

- mathematical reasoning
- paper analysis
- optimization formulation
- quantum-algorithm reasoning
- private documents
- larger coding jobs
- research synthesis

On the 36 GiB M3 Pro, the approximately 25–30B Q4 class is the upper range targeted for regular use.

### Tier D — Frontier models

Keep all three subscriptions, but assign them different responsibilities instead of asking them to perform the same work.

#### Claude — architect and critic

- architecture
- critique and review
- mathematical reasoning partnership
- research planning
- difficult debugging

#### Codex — implementation engineer

- repository modification
- test execution
- refactoring
- bug fixing
- experiment implementation

#### Gemini — large-context and multimodal specialist

- very large context
- multimodal material
- large document sets
- figures and screenshots
- independent second opinions
- Google ecosystem workflows

This division of labor keeps the frontier models complementary and makes the local stack responsible for the work that benefits most from privacy, low latency, and predictable cost.

### Current model policy

The authoritative installed/configured model table is maintained in the
[operator guide](docs/ATELIER_OPERATOR_GUIDE.md). Do not use an old download
roster from this README as an installation checklist. Add a model only after
assigning it a role, checking its memory budget, and defining an evaluation.
