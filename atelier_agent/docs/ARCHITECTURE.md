# Atelier Architecture

This document describes the current implementation. The forward-looking
product roadmap lives in [`docs/ATELIER_WORKBENCH_PLAN.md`](../../docs/ATELIER_WORKBENCH_PLAN.md),
and the concise frozen baseline is [`docs/CURRENT_ARCHITECTURE.md`](../../docs/CURRENT_ARCHITECTURE.md).

## Current system

```text
CLI / Web / Finder / persistent session / MCP
              │
       Atelier service/API
          ┌───┴────┐
          │        │
    knowledge    build/general
          │        │
       rag.answer  agent.react
          │        │
          └───┬────┘
              │
       shared guarded tools
       ┌──────┼────────┬────────┐
       │      │        │        │
     files  search   tests    memory
       │      │        │        │
       └──────┴────────┴────────┘
              │
  Qwen3-Embedding-4B / 2560D
              │
     ChromaDB + SQLite manifest
```

Atelier is local-first and model-agnostic. Ollama is the current local model
transport; MLX remains an Apple-Silicon experiment/provider surface and is not
required by the scientific-library runtime on Linux.

## Model roles

| Role | Current configuration | Status | Responsibility |
|---|---|---|---|
| `worker` | `hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K` | installed | fast extraction, classification, structured subtasks |
| `brain` | `qwen3:8b` | installed; temporary default | general reasoning and build mode |
| `coder` | `qwen3:8b` | installed and benchmarked | repository edits, tests, and small coding tasks |
| `heavy` | `gemma4:26b` | installed | hard reasoning and end-to-end local synthesis |
| `expert` | empty | intentionally unconfigured | reserved capability slot |
| `router` | `qwen3:4b` | configuration placeholder | future routing experiment |
| embedding | `qwen3-embedding:4b` | installed | 2,560-dimensional query/document embeddings |

`qwen3:14b` is no longer the active default because it is not installed on the
current Mac. It remains a future candidate; the temporary brain slot is
`qwen3:8b` until a larger model is deliberately evaluated.

The code does not assume that every configured model is installed. `doctor`
reports `ok`, `missing`, or `unconfigured` explicitly. No model is downloaded
merely to make a placeholder green. The coder selection is backed by the
frozen multi-file benchmark in `docs/archive/steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md`.

## Knowledge library

```text
source files
    ↓
SHA-256 document identity + SQLite manifest
    ├── unchanged   → skip extraction and embedding
    ├── relocated   → update path, reuse vectors
    ├── duplicate   → register alias, reuse vectors
    └── new/changed → extract → clean → section-chunk → embed → replace
    ↓
Qwen3-Embedding-4B / 2560D
    ↓
ChromaDB persistent collection
    + SQLite index manifest
    ↓
dense + BM25 → RRF → section adjustment → diversity → optional reranking
```

PDFs retain raw and cleaned page text, section labels, source paths, and
content-addressed metadata. Paper identity and subjective characterization
are separate strict Pydantic schemas. Memory uses a separate Chroma collection
and SQLite migration manifest.

Project memory is separate from semantic user memory. It stores explicit
project-scoped notes with optional expiry and provenance, plus structured
session, task, and artifact entities. Workflow task state is mirrored there;
conversation text is not automatically promoted to durable memory.

ChromaDB plus SQLite is the frozen current storage choice. LanceDB is not a
production dependency or an alternative store in the current architecture.

## Agent and tools

The current build loop is a deliberately small ReAct primitive:

```text
model JSON decision → one tool → bounded observation → next decision
```

The registry is shared by the CLI, agent, and MCP server. Current tool families
include file reads/writes, search, repository mapping, Python execution, test
running, AST edits, deterministic repository inspection, semantic search, and memory. File and execution tools now
receive an explicit persisted workspace context with approved roots and
capabilities. `LOCAL_ONLY` is the default privacy policy; this remains an
application-level boundary until stronger OS-level isolation is added.

Research network operations are separate and explicit: lookup results are
cached under the external runtime home with request provenance; graph lookup,
Crossref citation verification, and allowlisted paper download are exposed as
distinct tools. They require an attached `CLOUD_ALLOWED` workspace with the
network capability, and downloads write a sidecar URL/timestamp/hash record.

The coder role, explicit workspace manager, capability policy, typed
multi-file build workflow, and durable workflow engine are implemented as
application surfaces. Workflow runs persist typed state and checkpoints under
the external runtime home, pause at explicit approval gates, and can be
recovered or cancelled through the service/API.

## Runtime state

The active runtime stores user state outside the source checkout under
`~/Atelier` by default (or `ATELIER_HOME`). Its versioned layout separates
library, databases, workspaces, caches, logs, and backups. Development-era
state can be copied into that layout with `atelier state migrate`; the source
checkout remains preserved, and the migration writes a recoverable record.

## Reliability baseline

The frozen Scientific Library v1.0 baseline includes:

- incremental content-addressed ingestion;
- strict paper characterization and extraction caches;
- compatible Qwen3-Embedding-4B / 2560D index checks;
- hybrid retrieval and section-aware diversity;
- safe semantic-memory migration;
- Rich-safe rendering;
- a model-free Test workflow and clean-clone installation path;
- a real Gemma-backed grounded `atelier ask` smoke test.

The current live library contains three verified papers, and the clean-state
model-backed smoke has also been run from a fresh temporary runtime with fresh
Qwen3-Embedding-4B ingestion and a Qwen3-8B cited answer. The frozen
model-free v2 suite covers routing, workflows, memory isolation, security,
research denial, quantum, and optimization. These checks still do not claim
repository-scale statistical reliability, provider-backed Qiskit execution,
or hardened OS-level isolation; those remain explicit extensions.
