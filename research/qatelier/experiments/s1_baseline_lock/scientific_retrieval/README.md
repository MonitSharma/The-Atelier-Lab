# S1 scientific retrieval task definition

This directory defines the QAtelier S1 scientific-retrieval condition as a
reproducible, classical-first artifact. It uses SciFact from the BEIR
benchmark: scientific claims are queries and scientific abstracts are the
retrieval corpus. The committed artifact stores source revisions, file hashes,
schema counts, and the exact deterministic query selections; source data is
not vendored into the repository.

## Status and scope

Status: `reference_definition_ready`.

This is a task definition and split lock, not a completed baseline result.
It deliberately does not contact a quantum provider, run a circuit, or claim
quantum advantage. The standard SciFact test qrels remain reserved for a later
held-out evaluation and are not used to select representations, models, or
hyperparameters.

## Pinned sources

- Corpus and queries: `BeIR/scifact` at revision
  `b3b5335604bf5ee3c4447671af975ea25143d4f5`.
- Relevance judgments: `BeIR/scifact-qrels` at revision
  `2938d17dc3b09882fdb8c12bbbe2e2dc0e75a029`.
- The exact member URLs, SHA-256 digests, row counts, and column schemas are
  in [`data_manifest.json`](data_manifest.json).

The source data is licensed and attributed by the upstream dataset cards. The
repository commits only metadata and does not redistribute the data files.

## Representation and evaluation contract

The query/document text is encoded separately with the S0-frozen
`sentence-transformers/paraphrase-mpnet-base-v2` snapshot. For a corpus row,
the encoder input is `title + "\\n" + text` when a title exists, otherwise
`text`; query rows use the same rule. No relevance labels are used by the
encoder.

The intended low-dimensional QAtelier input is a train-only PCA compressor
fit on documents referenced by the selected training qrels, then applied to
all query and corpus embeddings. The default output dimension is 4. A
candidate reranker receives the frozen pair features
`[q, d, abs(q-d), q*d]` and must score the same query/document candidates as
the classical controls. This makes the quantum and classical comparisons
representation-matched; it does not assume that the quantum model is better.

The primary retrieval metrics are nDCG@10, MRR@10, and Recall@10, aggregated
over queries and then over the fixed confirmation seeds. Every report must
also state the number of corpus documents, queries, judged positives, and
candidate documents scored per query.

## Deterministic selections

[`split_manifest.json`](split_manifest.json) contains the materialized query
IDs for:

- training selections with seeds `11, 13, 17` and query counts `32, 64, 128`;
- five confirmation selections with seeds `101, 103, 107, 109, 113`, each of
  64 queries;
- the standard SciFact test qrels, which are reserved and never sampled by
  this S1 lock.

The selection rule uses sorted numeric query IDs and NumPy `PCG64` via
`default_rng(seed * 1000 + budget)`. Training selections use the first `n`
IDs from a seed-specific permutation, so smaller selections are nested in the
128-query selection. Confirmation queries are drawn from the train-qrels
holdout after removing the union of all 128-query training selections. The
confirmation selections may overlap one another, but never overlap the
training union.

## Reproduce or validate

Validate the committed metadata and regenerate the split deterministically:

```bash
.venv/bin/python \
  research/qatelier/experiments/s1_baseline_lock/scientific_retrieval/validate.py
```

To additionally validate downloaded files, place them in a directory matching
the member paths in `data_manifest.json` and pass `--data-dir`:

```bash
.venv/bin/python \
  research/qatelier/experiments/s1_baseline_lock/scientific_retrieval/validate.py \
  --data-dir /path/to/scifact-files
```

The validator performs no network access. A future preparation runner may use
the pinned URLs, verify all four hashes before reading any rows, encode with
the pinned S0 model, and write a preparation manifest under a later scoped
artifact directory.

