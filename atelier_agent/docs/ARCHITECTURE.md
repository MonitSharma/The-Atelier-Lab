# Atelier Architecture

This document describes the current implementation. The forward-looking
product roadmap lives in [`docs/ATELIER_WORKBENCH_PLAN.md`](../../docs/ATELIER_WORKBENCH_PLAN.md),
and the concise frozen baseline is [`docs/CURRENT_ARCHITECTURE.md`](../../docs/CURRENT_ARCHITECTURE.md).

## Current system

```text
CLI / persistent session / MCP
              │
       atelier application
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
| `brain` | `qwen3:14b` | configuration placeholder | general reasoning and build mode |
| `heavy` | `gemma4:26b` | installed | hard reasoning and end-to-end local synthesis |
| `expert` | empty | intentionally unconfigured | reserved capability slot |
| `router` | `qwen3:4b` | configuration placeholder | future routing experiment |
| embedding | `qwen3-embedding:4b` | installed | 2,560-dimensional query/document embeddings |

The code does not assume that every configured model is installed. `doctor`
reports `ok`, `missing`, or `unconfigured` explicitly. No model is downloaded
merely to make a placeholder green.

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

ChromaDB plus SQLite is the frozen current storage choice. LanceDB is not a
production dependency or an alternative store in the current architecture.

## Agent and tools

The current build loop is a deliberately small ReAct primitive:

```text
model JSON decision → one tool → bounded observation → next decision
```

The registry is shared by the CLI, agent, and MCP server. Current tool families
include file reads/writes, search, repository mapping, Python execution, test
running, AST edits, semantic search, and memory. File access is currently
anchored to the process workspace and is not yet a multi-workspace permission
system; that is the next product milestone.

The future `coder` role, explicit workspace manager, capability policy, and
multi-file transaction workflow are not yet implemented. They must be added
without weakening this low-level execution primitive.

## Runtime state

The current development runtime stores the local library and caches under
`atelier_agent/data/`. This is intentionally still repository-local. Step 19
will migrate user state to a versioned Atelier home with validation, backup,
and rollback; the source checkout and user library are not independent yet.

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

The current benchmark is a small local three-paper regression suite. It is not
evidence of repository-scale coding reliability, multimodal understanding,
security isolation, or general research-agent reliability. Those are separate
future evaluation milestones.
