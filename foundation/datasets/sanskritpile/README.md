# SanskritPile-v1

*A reproducible, deduplicated Sanskrit corpus for foundation model pretraining.*

---

## Background

As part of **The Atelier Lab**, we are investigating how language, corpus structure, and data quality influence the training dynamics of small foundation models under fixed compute budgets.

Our initial objective was straightforward:

> Compare English and Sanskrit pretraining under identical model architecture, optimizer, tokenizer size, and training budget on consumer hardware.

The first pilot experiment produced a surprising result.

A 73M parameter transformer trained on a 50 MB Sanskrit corpus converged dramatically faster than an equivalent English model, reaching a validation loss of **0.896 BPB**, compared to **1.792 BPB** for English.

At first glance, this appeared to support the hypothesis that Sanskrit possesses statistical properties that make it particularly favorable for transformer-based language modeling.

However, rather than accepting this result, we investigated the dataset itself.

---

# The Investigation

Corpus diagnostics revealed that the original Sanskrit dataset contained approximately **19.7% duplicate lines**.

Many of these duplicates originated from:

- repeated document headers
- verse numbering
- catalog metadata
- editorial boilerplate
- repeated sloka markers

Such repeated structures substantially increase statistical predictability.

A language model can exploit these artifacts, producing artificially low validation losses that do not necessarily reflect genuine linguistic understanding.

Rather than drawing premature conclusions about Sanskrit itself, we decided to rebuild the corpus from first principles.

---

# SanskritPile-v1

SanskritPile-v1 is the result of that investigation.

Rather than maximizing corpus size, the design prioritizes:

- reproducibility
- corpus diversity
- low duplication
- transparent preprocessing
- documented provenance

Every preprocessing step is scripted and reproducible.

No manual cleaning is performed.

---

# Pipeline

The dataset construction pipeline performs the following stages.

```text
Raw Sources
      │
      ▼
Download
      │
      ▼
Unicode Normalization
      │
      ▼
Cleaning
      │
      ▼
Document Deduplication
      │
      ▼
Paragraph Deduplication
      │
      ▼
Line Deduplication
      │
      ▼
Quality Filtering
      │
      ▼
Corpus Analysis
      │
      ▼
SanskritPile-v1
```

The pipeline automatically generates reports describing every stage of processing.

---

# Corpus Goals

The objective of SanskritPile-v1 is not to maximize the amount of Sanskrit text.

Instead, the corpus aims to provide a clean benchmark suitable for foundation-model pretraining.

Current design goals include:

- Duplicate line rate below 2%
- Unicode normalization
- Minimal OCR artifacts
- Minimal metadata leakage
- Multiple textual genres
- Fully reproducible generation pipeline

---

# Experimental Results

We repeated the original pretraining experiment using SanskritPile-v1.

## Original Pilot

| Dataset | Duplicate Lines | Validation BPB |
|----------|----------------:|---------------:|
| Original Sanskrit Corpus | 19.69% | **0.896** |

## SanskritPile-v1

| Dataset | Duplicate Lines | Validation BPB |
|----------|----------------:|---------------:|
| SanskritPile-v1 | **0.04%** | **2.195** |

The apparent performance advantage disappeared after removing duplicated content.

---

# Scientific Interpretation

The primary conclusion of this work is **not** that Sanskrit is easier or harder for transformer models.

Instead, the experiments demonstrate that **corpus quality can dominate apparent training performance**.

The initial improvement observed during pretraining was largely explained by highly repetitive structures present in the original corpus.

Once these artifacts were removed, the training dynamics changed substantially.

This result highlights the importance of careful dataset engineering before drawing conclusions about language-specific properties.

---

# Current Limitations

SanskritPile-v1 remains an initial release.

Several limitations remain.

- The corpus is relatively small (~50–100 MB).
- Classical literature is still overrepresented.
- Contemporary Sanskrit prose is comparatively limited.
- Additional source diversity is desirable.
- Comparisons currently focus on a single model size (73M).

Future versions will address these limitations through additional sources and improved quality control.

---

# Future Work

Planned improvements include:

- broader source coverage
- improved genre balancing
- additional quality metrics
- multilingual benchmarking
- tokenizer studies
- scaling-law experiments
- longer pretraining runs
- early-stopping analysis

---

# Repository Structure

```text
sanskritpile/

├── scripts/
├── configs/
├── reports/
├── metadata/
├── cleaned/
├── raw/
├── SanskritPile-v1/
└── README.md
```

Every artifact required to rebuild the corpus is included in this repository.

---

# Citation

If you use SanskritPile-v1 in research, please cite this repository and reference the accompanying documentation describing the corpus construction pipeline.

---

> **The goal of SanskritPile is not to demonstrate that Sanskrit is inherently superior for language modeling. The goal is to enable reproducible investigation into how corpus quality, linguistic structure, and dataset engineering influence transformer pretraining.**
