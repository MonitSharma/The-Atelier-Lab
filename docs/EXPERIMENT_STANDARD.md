# Experiment standard

Experiments live under `foundation/experiments/` or `atelier_agent/` and are indexed in [`../experiments/registry.yaml`](../experiments/registry.yaml). Each experiment README must answer: research question, hypothesis, controls, changed variables, hardware/software, seed, metrics, artifact locations, observations, limitations, and reproduction command.

The shared result schema is [`../benchmarks/schemas/result.schema.json`](../benchmarks/schemas/result.schema.json). Missing measurements remain missing; do not infer or fabricate values.
