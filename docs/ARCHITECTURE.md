# Atelier — architecture

How the pieces fit. Atelier is **one agent harness** that powers two capability
modes (knowledge + build) over a shared toolbox, runs entirely locally, and is
measured by a built-in eval harness. This document is the map; `PROJECT.md` is
the why, `docs/TESTING.md` is the how-to-verify.

## 10,000-foot view

```
                         ┌─────────────────────────────────────┐
        you ──────────▶  │            atelier CLI (typer)        │
                         │  ask · chat · agent · remember ·      │
                         │  recall · eval · mcp · doctor · tools │
                         └──────┬───────────────────────┬────────┘
                                │                       │
                  knowledge mode│                       │build / general
                                ▼                       ▼
                       ┌─────────────────┐     ┌───────────────────────┐
                       │  rag.answer     │     │   agent.react          │
                       │  (grounded QA)  │     │   ReAct engine         │
                       └───────┬─────────┘     │  reason→act→observe    │
                               │               └───────┬───────────────┘
                               ▼                       │ JSON tool calls
                       ┌─────────────────┐             ▼
                       │ rag.retrieve    │     ┌───────────────────────┐
                       │ dense+BM25 (RRF)│     │  tools.registry        │
                       │ + optional rerank│    │  (one toolbox)         │
                       └───────┬─────────┘     └───────┬───────────────┘
                               │                       │
        ┌──────────────────────┼───────────────────────┼─────────────────┐
        ▼                      ▼                        ▼                 ▼
  ┌───────────┐        ┌──────────────┐        ┌──────────────┐   ┌────────────┐
  │ rag.embed │        │  rag.store   │        │ build tools  │   │  memory    │
  │ bge (MPS) │        │  ChromaDB    │        │ files/exec/  │   │ remember/  │
  └───────────┘        │  (vectors)   │        │ test/repo_map│   │ recall     │
                       └──────────────┘        └──────────────┘   └────────────┘
                               ▲                        │                 ▲
                               │                        ▼                 │
                       ┌───────┴────────┐       ┌──────────────┐   ┌──────┴─────┐
                       │ agent.brain    │◀──────│ tools run     │   │ ChromaDB   │
                       │ Ollama client  │       │ locally,      │   │ (memory    │
                       │ qwen3 / gemma  │       │ sandboxed     │   │ collection)│
                       └────────────────┘       └──────────────┘   └────────────┘

         Everything above runs on-device. Network egress: only the local
         Ollama endpoint + a one-time embedding/reranker model download.
```

## The layers

### 1. Models — `agent/brain.py`
A thin client over local **Ollama**. Three *roles*, chosen by task size rather
than hard-coded names:

| Role | Model | Use |
|---|---|---|
| `brain` | `qwen3:14b` | reasoning, build mode |
| `worker` | `qwen3:4b` | cheap subtasks, the LLM-judge |
| `heavy` | `gemma4:26b` | hardest reasoning (`--heavy`) |

Features: JSON-only mode (reliable tool calls), streaming, and qwen3
`<think>`-trace stripping. `health()` powers `atelier doctor`.

### 2. Tools — `tools/`
Every capability is a `Tool` (name, description, JSON input schema, function
returning a status dict). The `ToolRegistry` validates and dispatches calls.
One registry is the single source of truth, consumed by both the ReAct loop and
the MCP server.

- **Build:** `read_file` / `write_file` / `edit_file` (workspace-sandboxed),
  `ast_edit` (compile-checked Python function body replacement), `code_exec`
  (subprocess + timeout + macOS seatbelt network deny), `test_runner` (pytest,
  parsed — the *verifier*), `repo_map` (AST outline), `search` (local grep).
- **Knowledge:** `search_notes` (semantic RAG as a tool).
- **Memory:** `remember`, `recall`.
- **Opt-in:** `shell` (powerful, lightly guarded).

### 3. Knowledge mode — `rag/`
`ingest` (md/txt/pdf/code) → `chunk` (heading-aware) → `embed`
(`bge-base-en-v1.5` on MPS) → `store` (ChromaDB, cosine). At query time,
`retrieve` runs **dense + BM25** and fuses them with **Reciprocal Rank Fusion**,
with an **optional cross-encoder reranker**. `answer` feeds the top chunks to the
brain under a strict "answer only from context, cite sources" prompt.

### 4. The agent — `agent/react.py`
The general ReAct engine: reason → call one tool → observe → repeat → final
answer. Key reliability properties:
- **JSON mode** every turn → tool calls parse.
- **Reflection**: tool/parse errors are fed back as observations, not crashes.
- **Observation capping**: big outputs are truncated before re-entering context.
- **Trace logging**: every run → `data/traces/<ts>.json`.
- **Optional memory recall** seeds the system prompt (`use_memory`).

### 5. Memory — `agent/memory.py`
Discrete facts embedded into their own ChromaDB collection; recalled by semantic
similarity. Persistent across sessions (on disk), shares the embedding model.

### 6. MCP server — `atelier/mcp_server.py`
Publishes the registry over MCP stdio so external hosts can use Atelier's tools.
Same schemas as the local loop — no duplication.

### 7. Evaluation — `eval/`
Two **frozen** suites (`tasks_docqa/`, `tasks_code/`), deterministic metrics
(keyword coverage, retrieval hit@k, citation rate) + optional local LLM-judge,
a runner that executes code tasks in isolated `.eval_workspace/` copies and
verifies with the real pytest runner, JSON reports, and a **regression gate**
(`--gate`) that fails on any drop vs. the last report.

## Data & control flow: "ask my notes"
1. `atelier ask "Q"` → `rag.answer.answer_question`
2. `retrieve(Q)` → embed query → dense (ChromaDB) + BM25 → RRF → (rerank) → top-k
3. `format_context` numbers + truncates the chunks
4. `brain.chat` (grounded prompt) → cited answer

## Data & control flow: "fix the failing test"
1. `atelier agent "fix sample_task/"` → `ReActAgent.run`
2. brain emits a JSON tool call → registry executes → observation appended
3. typical arc: `repo_map → read_file → edit_file` or `ast_edit` → `test_runner`
4. agent finalizes only when `test_runner.passed_clean` is true; trace saved

## Hard constraints honored (PROJECT.md §1)
Local-only, $0, single Mac, ≤36 GB. The only network calls are to local Ollama
and one-time model downloads. Code execution is sandboxed; file/test tools are
pinned to the workspace.

## What's intentionally *not* here
No cloud APIs, no hosted vector DB, no always-on service, and no multi-agent
orchestrator yet. The fine-tuned router is present as a local component, but the
main build loop is still a single ReAct agent.
