# S0 — published-style reproduction and calibration

Status: preregistered, not run.

S0 is a calibration experiment, not a novelty claim. It asks whether the
QAtelier implementation can reproduce the qualitative behavior of a compact
frozen-sentence-encoder quantum-head setup while making the representation,
split, compression, classical controls, seeds, and finite-shot condition
explicit.

## Protocol

- Primary encoder: `sentence-transformers/paraphrase-mpnet-base-v2`.
- Dataset: SST-2 / a versioned low-data split compatible with the published
  frozen sentence-encoder setting.
- Heads: logistic regression, SVM, matched MLP, and a small QAtelier PQC.
- QAtelier normalization: one train-only compressor fitted on the frozen
  embeddings and reused by every head.
- Evaluation: development selection, held-out confirmation, exact simulator,
  finite-shot simulator, and resource accounting.
- Hardware: none in S0. IBM and Helios-1E are downstream validation stages.

The exact model revision, weights digest, dataset version, split manifest, and
cached embedding hash must be filled in `config.yaml` before `run.py` is
allowed to execute. Missing values are an intentional execution block, not a
permission to substitute the latest model or a test-derived split.

## Reproduction

The runner is intentionally not declared complete until the locks above exist.
The eventual command will be:

```bash
python -m research.qatelier.experiments.s0_reproduction.run \
  --config research/qatelier/experiments/s0_reproduction/config.yaml
```

Any reproduction discrepancy should be recorded as a discrepancy, not hidden
by changing the QAtelier-normalized protocol after seeing held-out results.
