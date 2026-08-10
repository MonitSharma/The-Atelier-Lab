# S0 — published-style reproduction and calibration

Status: completed calibration; negative result archived.

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
preparation-manifest hashes are committed. The embedding cache and fitted
compressor arrays used to produce the archived result remain in the external
output directory recorded by `preparation_validation.json`; they are not
claimed to be distributable repository artifacts. The completed raw bundle and
analysis are archived under `raw/` and `analysis/`.

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

The completed panel can be reproduced from an external prepared cache with:

```bash
python -m research.qatelier.experiments.s0_reproduction.run \
  --config research/qatelier/experiments/s0_reproduction/config.yaml
```

After preparation, the fixed S0 panel can be executed against that external
cache:

```bash
python -m research.qatelier.experiments.s0_reproduction.run \
  --config research/qatelier/experiments/s0_reproduction/config.yaml \
  --run \
  --prepared-dir /path/to/s0-prepared \
  --output-dir /path/to/new/s0-raw
```

`--selection-limit` and `--candidate-limit` are available only for bounded
runtime smoke checks; those outputs are explicitly marked partial and are not
scientific results. The committed full result is hash-linked by
[`s0_completion.json`](s0_completion.json).

Any reproduction discrepancy should be recorded as a discrepancy, not hidden
by changing the QAtelier-normalized protocol after seeing held-out results.
