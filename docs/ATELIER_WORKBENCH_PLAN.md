# Atelier Workbench Roadmap

This is the current-state product roadmap. It is not a historical account of
the original build order. Historical benchmark and implementation notes remain
in the Step reports and project changelog.

## Product destination

Atelier is a local-first, model-agnostic workbench over the user's approved
files, documents, repositories, research sources, and deterministic tools.

```text
CLI / Web / Finder
        ↓
local Atelier service
        ↓
workspace + privacy policy
        ↓
characterize → route → retrieve → tools → reason → verify → escalate
        ↓
artifacts, provenance, memory, and audit trail
```

Cloud models remain optional handoff targets. The local system must remain
useful offline and unpublished material must not leave the machine implicitly.

## Current baseline

Scientific Library v1.0 is frozen and tagged. It provides:

- content-addressed incremental ingestion;
- PDF extraction, paper identity, and characterization caches;
- Qwen3-Embedding-4B / 2,560D retrieval;
- ChromaDB plus SQLite manifest storage;
- dense + BM25 + RRF retrieval with section-aware ranking;
- semantic memory migration with backup and verification;
- Ollama worker/heavy model integration;
- CLI, persistent session, MCP, and Rich-safe output;
- declared dependencies, clean-clone reproduction, CI, and protected `master`;
- explicit persisted workspaces with capability-scoped tool contexts and
  `LOCAL_ONLY` as the default privacy policy.

The current development state is still repository-local and primarily textual.
Runtime state migration remains future work. See
[`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md).

## Dependency-ordered milestones

### Step 04.2 — Core consolidation

Keep `master` canonical, develop each milestone on a fresh feature branch,
protect `master`, eliminate stale architecture descriptions, and maintain one
current roadmap. Freeze as `atelier-core-v1.0`.

### Step 05 — Workspace and permission architecture — complete

Add:

```text
atelier workspace add PATH
atelier workspace open NAME
atelier workspace list
atelier workspace close NAME
```

Implemented with approved roots and explicit `read`, `write`, `execute`, and
`network` capabilities. Multiple attached roots, path and symlink escape
rejection, `LOCAL_ONLY` default privacy, and context-aware tool dispatch are
covered by tests. Destructive-operation confirmations and the hardened trust
boundary remain Step 17 work.

### Step 06 — Repository intelligence — complete

Build deterministic repository inspection before selecting a coding model:

- Git state, history, diff, and cleanliness;
- file tree, languages, package managers, environments, and test frameworks;
- entry points, important files, symbols, imports, references;
- test-to-source relationships and repository search;
- CLI commands: `repo inspect`, `repo status`, `repo symbols`, `repo search`,
  and `repo tests`.

Implemented as a standard-library deterministic inspector with Git, language,
environment, package, test, entry-point, symbol/import, test-link,
important-file, and bounded-search outputs. CLI and agent-tool interfaces are
available, and multi-file fixtures verify the structure-first behavior. Full
semantic indexing remains selective and deferred until the coder benchmark.

### Step 07 — Coding specialist benchmark — complete

Add a real `coder` model role. Research current local candidates at execution
time and benchmark approximately three 7–14B candidates against Gemma and the
worker on identical repository tasks. Record solve rate, test pass rate,
unnecessary reads, invalid edits, tool errors, latency, memory, and tokens.

Implemented with `atelier benchmark-coding`, three frozen multi-file tasks, and
the selected `qwen3:8b` coder role. The full comparison is recorded in
[`steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md`](steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md).

### Step 08 — Build Agent v2 — complete

Keep the current ReAct loop as the low-level primitive. Add a typed coding
workflow:

```text
inspect → plan → identify files → baseline tests → edit
       → targeted tests → regression tests → diff review → certificate
```

Add checkpoints, rollback, evidence requirements, multi-file transactions, and
measurable escalation from coder to a larger reasoner.

Implemented as `agent.coding_workflow.BuildWorkflow` and exposed through
`atelier code-fix`. It performs deterministic inspection and baseline tests,
issues a typed protocol to the coder, records tool evidence, runs an independent
regression suite and `git diff --check`, can retry with the brain role, and
produces a structured certificate. Checkpoints preserve clean baseline files,
remove workflow-created files on opt-in rollback, and preserve pre-existing
dirty paths.

### Step 09 — Capability router

Classify domain first—paper, code, data, vision, research, quantum,
optimization, or general—then choose the cheapest capable workflow. Decisions
must include modality, tools, privacy, context, difficulty, memory, abstention,
and escalation conditions.

### Step 10 — Model lifecycle

Create a registry containing role, model ID, quantization, memory estimate,
context, modality, JSON/tool support, and measured performance. Add
`atelier models list`, `status`, and `bench`. Track Ollama residency and avoid
unnecessary simultaneous large-model loads.

### Step 11 — Multimodal scientific documents

Keep native PDF extraction first. Add vision only for poor text quality or
figures, diagrams, tables, equation images, and scans. Support figure/caption
pairing, page citations, table extraction, and OCR fallback with visual tests.

### Step 12 — General file workbench

Create typed `ArtifactProfile` adapters for CSV, JSON, Parquet, SQLite,
spreadsheets, images, LaTeX, notebooks, presentations, and text. Deterministic
parsers must report schema, shape, types, missingness, formulas, references,
and previews before model reasoning.

### Step 13 — Research tools

Add explicitly networked, provenance-tracked tools for DOI metadata, arXiv,
Crossref, Semantic Scholar, search, citations, related work, and paper
downloads. Unpublished local content must never become an external query by
default.

### Step 14 — Quantum and optimization tools

Add deterministic Qiskit circuit inspection, resource counting, transpilation,
small simulation, and backend comparison. Add LP/MIP/QUBO validation, solver
integration, feasibility/objective verification, and solution comparison. The
LLM explains tool results; it does not invent them.

### Step 15 — Explicit workflows

Introduce typed workflows such as `paper_fast`, `paper_deep_read`,
`paper_compare`, `repo_inspect`, `code_fix`, `data_analyze`,
`research_verify`, `quantum_analyze`, and `optimization_validate`. Include
checkpoints, recovery, and human approval gates. LangGraph is optional.

### Step 16 — Project memory v2

Separate durable user facts, task state, source-derived notes, projects,
artifacts, decisions, provenance, and expiration. Add explicit remember,
forget, export/import, and project isolation. Do not persist every conversation
automatically.

### Step 17 — Security and trust boundary

Make capabilities mechanically enforceable. Add command allowlists, path
scopes, secret redaction, prompt-injection tests, tool-output protection,
destructive confirmations, audit logs, and opt-in raw shell access.

### Step 18 — Backend service/API

Separate application operations from Typer behind a local service layer for
workspaces, tasks, library, search, models, workflows, memory, and artifacts.
CLI and UI must call the same backend.

### Step 19 — Externalize runtime state

Move user state from `atelier_agent/data/` to a versioned Atelier home with
separate library, databases, workspaces, config, caches, logs, and backups.
Provide migration, validation, rollback, and repair.

### Step 20 — Web workbench

Build a replaceable UI over the backend with workspace, library, source/context,
paper cards, model status, traces, approvals, privacy mode, and workflow views.

### Step 21 — Finder integration

Add opt-in Quick Actions such as Send to Atelier, Add to Library,
Characterize Paper, Explain File, and Ask Atelier. Honor workspace permissions;
do not silently watch or index the Mac.

### Step 22 — Frontier handoff

Create explicit user-approved handoff bundles for Claude, Codex, and Gemini
containing task, selected context, evidence, constraints, and requested output.
Keep local operation independent of cloud access.

### Step 23 — Reliability science v2

Expand evaluation to repository, visual-document, data, research-verification,
routing, injection, memory-isolation, quantum, optimization, and end-to-end
tasks. Add confidence intervals, repeated trials, latency/memory/cost metrics,
failure taxonomies, frozen test sets, and baseline comparisons.

### Step 24 — Performance engineering

Measure cold start, time-to-first-token, embedding throughput, retrieval/index
latency, peak unified memory, model swaps, disk use, long-session stability,
and service concurrency. Optimize only from traces.

### Step 25 — Packaging and release engineering

Add one supported install path, `atelier init`, config generation, model setup,
schema migrations, backup/restore, export/import, health repair, macOS smoke
validation, changelog, semantic versions, and signed release tags.

### Step 26 — Atelier v1.0 acceptance

Verify the complete clean-Mac scenario: install, initialize, attach workspace,
ingest and characterize a paper, answer with citations, inspect and modify a
repository with tests, analyze structured data, inspect a figure, run quantum
or optimization tools, preserve project memory, remain offline under
`LOCAL_ONLY`, create an optional handoff, use CLI and UI, restart, recover, and
pass the full reliability, security, and performance suites.

## Separate expertise roadmap

`ROADMAP.md` remains the personal AI expertise roadmap: transformers,
pretraining, alignment, systems, kernels, and eventual research contribution.
It is valuable but is not the dependency graph for shipping the Atelier product.

```text
product:   Library → Workspace → Repo → Coder → Router → Vision → Files
           → Research/Domain → Workflows → Security → API → UI → Finder
           → Handoffs → Reliability/Performance → Atelier v1.0

expertise: Transformers → Pretraining → Alignment → Systems → Research
```

## Model policy

Do not download missing placeholder models merely to make `doctor` green. Add a
model only when its role has a frozen benchmark, a memory budget, and a clear
workflow consumer. The current installed baseline is LFM worker, Qwen3
embedding, and Gemma heavy reasoner.
