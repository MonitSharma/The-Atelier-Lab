# Atelier package

This directory contains the installable Atelier application: the CLI, local
RAG pipeline, ReAct agent, guarded tools, evaluations, and runtime services.

For user-facing operation, use the repository-level guides:

- [`docs/START_HERE.md`](../docs/START_HERE.md) — choose a path.
- [`docs/ATELIER_OPERATOR_GUIDE.md`](../docs/ATELIER_OPERATOR_GUIDE.md) — run
  the CLI, understand the architecture, and see the model roles.
- [`docs/WORKING_WITH_DOCUMENTS.md`](../docs/WORKING_WITH_DOCUMENTS.md) —
  ingest papers, notes, and the QAtelier research plan.
- [`docs/CURRENT_ARCHITECTURE.md`](../docs/CURRENT_ARCHITECTURE.md) — frozen
  current-state architecture.
- [`docs/CURRENT_RESULTS.md`](../docs/CURRENT_RESULTS.md) — measured results
  and their limits.

## Install for development

From the repository root:

```bash
uv venv .venv
uv pip install -r atelier_agent/requirements.txt
uv pip install -e atelier_agent
```

The global macOS launcher at `~/bin/atelier` uses this editable environment,
so normal use does not require activating the virtual environment:

```bash
atelier
atelier doctor
```

Atelier uses Ollama on `localhost`. The configured roles and whether each model
is actually installed are reported by `atelier doctor`; a missing placeholder
is not automatically downloaded.

## Developer checks

```bash
make -C atelier_agent test
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
```

The full model-backed reproduction is intentionally separate and can download
models or create runtime state:

```bash
make -C atelier_agent reproduce
```

## Package layout

```text
atelier_agent/
├── atelier/       CLI, configuration, session, service, web, MCP, workspaces
├── agent/         ReAct loop, model routing, memory, project workflows
├── rag/           ingestion, paper extraction, embeddings, retrieval, answers
├── tools/         guarded file, code, search, repository, science, and memory tools
├── repo/          deterministic repository inspection
├── eval/          frozen task suites, fixtures, metrics, and reports
├── models/        model-role registry and router adapters
├── tests/         deterministic unit and acceptance tests
└── docs/          developer architecture, testing, evaluation, and writeup notes
```

User documents, vector indexes, traces, caches, memory, and workflow state are
stored outside this checkout under `~/Atelier` by default. The frozen document
QA inputs live under [`eval/fixtures/docqa_corpus/`](eval/fixtures/docqa_corpus/)
solely to preserve historical benchmark comparability; they are not current
project instructions.

## Design boundary

The system is local-first. Knowledge mode retrieves from explicitly ingested
files and produces cited answers. Build mode inspects an approved workspace,
uses guarded tools, runs tests, and reports verification. `LOCAL_ONLY` is the
default privacy policy; network research and external handoffs are explicit
operations.
