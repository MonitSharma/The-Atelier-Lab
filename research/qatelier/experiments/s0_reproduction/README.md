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

The exact model revision, weights digest, dataset version, and split manifest
are committed. The cached embedding and compressor hashes are produced by the
credential-free preparation command; missing values are an intentional
execution block, not a permission to substitute the latest model or a
test-derived split.

## Reproduction

Preparation is explicit and writes only to a new, caller-selected output
directory. The archive and encoder are not stored in this repository:

```bash
python -m research.qatelier.experiments.s0_reproduction.run \
  --config research/qatelier/experiments/s0_reproduction/config.yaml \
  --prepare \
  --archive /path/to/SST-2.zip \
  --encoder-path /path/to/pinned/paraphrase-mpnet-base-v2 \
  --output-dir /path/to/new/s0-prepared
```

The command verifies the archive/member hashes, model weights digest, exact
sample selections, and embedding shape. It then writes an embedding cache,
representation manifest, and one train-only PCA artifact per declared
selection. The normal experiment runner remains gated until those generated
artifacts are explicitly supplied and the downstream head protocol is locked.

The eventual execution command is:

```bash
python -m research.qatelier.experiments.s0_reproduction.run \
  --config research/qatelier/experiments/s0_reproduction/config.yaml
```

Any reproduction discrepancy should be recorded as a discrepancy, not hidden
by changing the QAtelier-normalized protocol after seeing held-out results.
