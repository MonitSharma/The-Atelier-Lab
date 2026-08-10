# Steps 11–12 — Visual Documents and Artifact Workbench

Status: **complete**

## Scientific PDF evidence

`rag.visual.analyze_pdf` preserves native text extraction as the first path and
identifies pages that need visual fallback. It reports page-level citations,
character counts, poor-text quality, figure/caption pairs, and optional PNG
renders. The CLI is:

```bash
atelier paper-visual paper.pdf --json
atelier paper-visual paper.pdf --render
atelier paper-visual paper.pdf --ocr --json
```

The output is deterministic and local. It does not silently send a page or
unpublished paper to an external vision service.

Page evidence also reports optional table headers/counts and an explicit OCR
status. OCR is opt-in for poor-text pages and never replaces native extraction
silently.

The typed `figure_inspect` workflow now exposes the same sequence as a durable
operation: locate pages → render evidence → approval-gated visual
interpretation → page citations. If no multimodal model input is approved, the
workflow returns the rendered evidence and an explicit interpretation-needed
status rather than inventing a visual conclusion.

## Typed file profiles

`files.artifacts.profile_path` returns a typed `ArtifactProfile` before a model
sees the artifact. It supports CSV/TSV, JSON records, Parquet, SQLite,
spreadsheets, images, text, LaTeX, notebooks, archives, and PDF handoff hints.
Profiles include kind, size, shape, schema, inferred types, missingness,
formulas, references, previews, and warnings.

```bash
atelier profile results.csv --json
atelier profile experiment.sqlite3
```

## Verification

Tests cover CSV schema/missingness, JSON records, SQLite tables, and PDF
figure/citation evidence. Runtime render output is ignored as local cache; only
the deterministic profiler and frozen tests are committed.
