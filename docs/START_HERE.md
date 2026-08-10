# Start here

The Atelier Lab is a local-first research laboratory for learning language models, measuring Apple Silicon systems, and building reliable agents under a fixed 36 GB unified-memory budget.

Choose one path:

- **Learn language models:** begin with [tensors and probability](../learning/00_tensors_and_probability/README.md), then follow the numbered modules.
- **Run Atelier:** read the [operator guide](ATELIER_OPERATOR_GUIDE.md), then use the [document workflow](WORKING_WITH_DOCUMENTS.md) for papers, notes, and research plans.
- **Understand QAtelier:** follow the [QAtelier quickstart](WORKING_WITH_DOCUMENTS.md#qatelier-quickstart).
- **Reproduce experiments:** browse the [experiment registry](../experiments/registry.yaml), read the [experiment standard](EXPERIMENT_STANDARD.md), and follow each experiment's own README.

The central question is: *How much reliable AI capability can one researcher obtain from local models under fixed memory, latency, privacy, and compute constraints?*

The package-level developer notes are in [atelier_agent/README.md](../atelier_agent/README.md). The active implementation and runtime state are separate: code lives in `atelier_agent/`, while user library data lives under `~/Atelier`.
