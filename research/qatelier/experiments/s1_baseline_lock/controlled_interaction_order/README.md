# S1 controlled interaction-order benchmark

This directory is a self-contained, generated definition of the mandatory
QAtelier mechanism benchmark. It fixes interaction orders `k ∈ {1, 2, 3, 4,
5, 6}` before any architecture search or hardware execution. The benchmark is
small enough to run locally and contains no provider credentials, provider
calls, or quantum jobs.

## Scientific question

For a frozen representation and equal low-data budgets, does the difference
between a QAtelier quantum adapter and strong classical controls change
systematically with the order of the latent target? A result is mechanistic
only if it survives the nonlinear, Fourier/spectral, kernel, and tensor
controls specified by the governing QAtelier plan. This artifact defines the
data; it does not claim a quantum advantage.

## Exact target construction

Every `(family, order)` pair creates one latent `InteractionProblem` using the
canonical `research.qatelier.benchmark.make_interaction_problem` API. The
problem seed is exactly:

```text
problem_seed = 314159 + 100 * order + family_index
```

There are six standard-normal features. The four frozen families are:

| Artifact name | Canonical family | Latent score |
| --- | --- | --- |
| `aligned_polynomial` | `aligned` | `x[0] · x[1] · … · x[k-1]` |
| `rotated_polynomial` | `rotated` | Product of the first `k` coordinates after one frozen orthogonal rotation |
| `misaligned_dense` | `misaligned` | Product of `k` normalized dense projections |
| `fourier_trigonometric` | `fourier` | Product of `sin(pi * frequency_i * u_i / 2)` |

The exact rotation, dense directions, and Fourier frequencies are determined
by the problem seed and are recorded through the target fingerprint in
`manifest.json`. Labels are binary and use a single predeclared boundary:

```text
y = 1 if score(x) >= 0.0 else 0
```

No split recalibrates the threshold, and no observation or label noise is used
in this baseline definition.

## Exact train/confirmation protocol

For every one of the 24 `(family, order)` problems:

* train selections use seeds `11, 13, 17`;
* confirmation seeds are `101, 103, 107, 109, 113`;
* each split contains exactly 256 examples of class 0 followed by 256 of
  class 1;
* the deterministic sampler consumes standard-normal candidates in blocks of
  4096 until it has collected those rows;
* train budgets are prefixes of each class: `16, 32, 64, 128, 256` per class;
* confirmation data are fixed, independent, and never used for fitting,
  tuning, compression, or candidate selection.

The resulting bundle has 192 split records and stores the exact feature and
label arrays in `data/controlled_interaction_order.npz`. `manifest.json`
contains the data index, target fingerprints, class counts, split hashes, and
the row indices that implement every training budget. `validation.json`
contains the independently checked array hash and provider/job safety fields.

## Reproduce and validate

From the repository root, regenerate the artifact in a fresh directory:

```bash
PYTHONPATH=. .venv/bin/python \
  research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order/generate.py \
  --output-dir /tmp/qatelier-controlled-order
```

Validate the checked-in bundle without rewriting it:

```bash
PYTHONPATH=. .venv/bin/python \
  research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order/generate.py \
  --check-dir research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order
```

The generation script only constructs local NumPy arrays and imports the
canonical QAtelier benchmark. It has no hardware/provider integration.

The classical reference panel is archived under [`raw/`](raw/). It contains
14,400 rows: 24 family/order problems × 3 training seeds × 5 budgets × 5
confirmation seeds × 8 heads. The panel uses the frozen six-dimensional
features directly, records train/confirmation split fingerprints, and makes no
candidate selection or quantum claim.
