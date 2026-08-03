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
- [Experiment registry](experiments/registry.yaml)
- [Repository map](docs/REPOSITORY_MAP.md)

## Quick start

```bash
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
make -C atelier_agent test       # requires the project's .venv
```

The educational `foundation/minillm` package is CPU-friendly and has no dataset download step. The agent remains self-contained under `atelier_agent/`; existing CLI, RAG, tools, evaluation, router, MCP, and reproduction commands are preserved.

## Active phase

The current phase closes the foundation learning loop: understand the primitives in `learning/`, run the offline `minillm` exercises, then deepen quantization and serving measurements without weakening reproducibility.
