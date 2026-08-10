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
  `LOCAL_ONLY` as the default privacy policy;
- an active external runtime home at `~/Atelier` with migrated and verified
  three-paper retrieval state;
- durable workflow/task state, project/session/task/artifact memory, and a
  shared service/API used by the CLI and replaceable web UI.

The deterministic foundation and the clean-state local model evidence for Step
26 are now verified on the current macOS development line. Optional provider
integrations, hardened OS isolation, signed artifacts, and remote publication
remain explicitly scoped extensions. See [`CURRENT_ARCHITECTURE.md`](CURRENT_ARCHITECTURE.md).

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
covered by tests. Destructive-operation confirmations, secret redaction,
untrusted-output marking, and audit logging are implemented at the current
capability boundary; broader OS-level isolation remains a future extension.

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
[`archive/steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md`](archive/steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md).

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

### Step 09 — Capability router — complete

Classify domain first—paper, code, data, vision, research, quantum,
optimization, or general—then choose the cheapest capable workflow. Decisions
must include modality, tools, privacy, context, difficulty, memory, abstention,
and escalation conditions. Implemented with the deterministic
`CapabilityRouter`, including LOCAL_ONLY network abstention, explicit
escalation conditions, and a frozen 16-case human-labeled evaluation
(`atelier route-eval`, currently 16/16).

### Step 10 — Model lifecycle — complete

Create a registry containing role, model ID, quantization, memory estimate,
context, modality, JSON/tool support, and measured performance. Add
`atelier models list`, `status`, and `bench`. Track Ollama residency and avoid
unnecessary simultaneous large-model loads.

Implemented with `ModelLifecycle` and the `atelier models` command group. The
registry records role, model ID, quantization estimate, memory/context budget,
modality, tool/JSON support, install state, and Ollama residency; `bench` uses
the frozen coding benchmark and saves its report.

### Step 11 — Multimodal scientific documents — complete

Keep native PDF extraction first. Add vision only for poor text quality or
figures, diagrams, tables, equation images, and scans. Support figure/caption
pairing, page citations, table extraction, and OCR fallback with visual tests.

Implemented deterministic PDF page evidence with text-quality flags,
figure/caption pairing, page citations, and targeted page rendering via
`atelier paper-visual`. Model vision remains a fallback consumer of these
artifacts rather than the first PDF parser.

### Step 12 — General file workbench — complete

Create typed `ArtifactProfile` adapters for CSV, JSON, Parquet, SQLite,
spreadsheets, images, LaTeX, notebooks, presentations, and text. Deterministic
parsers must report schema, shape, types, missingness, formulas, references,
and previews before model reasoning.

Implemented with `files.artifacts` and `atelier profile` for common tabular,
database, image, text, notebook, spreadsheet, archive, and PDF inputs.

### Step 13 — Research tools — complete

Added explicitly networked, provenance-tracked tools for DOI metadata, arXiv,
Crossref, Semantic Scholar, related/cited-by work, citation verification, and
allowlisted paper downloads. Results are cached under the external runtime
home; unpublished local content never becomes an external query by default.

### Step 14 — Quantum and optimization tools — complete

Added deterministic OpenQASM/Qiskit-aware circuit inspection, optional Qiskit
transpilation with an explicit unavailable result, bounded NumPy statevector
simulation, provider-free backend capacity comparison, SciPy LP solving when
available, exact small-binary QUBO solving, feasibility/objective verification,
and candidate comparison. Provider-backed backends and optional external solver
packages remain explicit extensions.

### Step 15 — Explicit workflows — complete

Introduced typed workflow specifications for `paper_fast`, `paper_deep_read`,
`paper_compare`, `figure_inspect`, `repo_inspect`, `code_fix`, `data_analyze`,
`research_verify`, `quantum_analyze`, and `optimization_validate`, including
steps, capabilities, recovery, and human approval gates. A durable JSON
execution engine now persists typed state and per-step checkpoints, pauses for
approval, and supports recovery/cancellation through the service/API.
LangGraph remains optional.

### Step 16 — Project memory v2 — complete

Separated project-scoped durable facts, task state, source-derived notes,
artifacts, decisions, provenance, and expiration in a dedicated SQLite store.
Added structured session/task/artifact entities, workflow task mirroring,
explicit remember/forget/export/import, project isolation, and CLI commands.
Conversations are not persisted automatically.

### Step 17 — Security and trust boundary — complete

Made capabilities mechanically enforceable at registry dispatch. Added a shell
allowlist, path/capability scopes, secret redaction, untrusted tool-output and
prompt-injection markers, persisted one-use destructive confirmations, audit
logs, and opt-in raw shell access. OS-level sandbox hardening remains future
work.

### Step 18 — Backend service/API — complete

Separated application operations from Typer behind a local service layer for
workspaces, tasks, library, search, models, workflows, memory, artifacts,
uploads, source viewing, paper actions, repository actions, and approvals.
Added a loopback JSON HTTP API over that service. CLI and UI use the same
backend contract; daemon authentication and stronger process isolation remain
later hardening work.

### Step 19 — Externalize runtime state — complete

Added and activated a versioned Atelier home with
separate library, databases, workspaces, config, caches, logs, and backups.
Added `atelier init`, state planning, validation, copy migration, and
record-scoped rollback. Existing repository state is preserved; the migrated
three-paper library was reindexed and verified at 223 chunks.

### Step 20 — Web workbench — complete

Built a replaceable, dependency-free local UI at `/ui` over the backend with
workspace/privacy state, library, model status, traces, approvals, chat/task
input, route/search forms, source viewing, bounded upload, paper actions, and
repository actions.

### Step 21 — Finder integration — complete

Added explicit Finder/Shortcuts-compatible planning and an executable macOS
entrypoint for Send to Atelier, Add to Library, Characterize Paper, and Explain
File. Actions honor workspace permissions and never silently watch or index
the Mac.

### Step 22 — Frontier handoff — complete

Created explicit local handoff bundles for Claude, Codex, and Gemini
containing task, selected context, evidence, constraints, and requested output.
Selected workspace files are validated and secret-redacted before optional
content inclusion. External approval is recorded separately and no provider
call is made by bundle creation.

### Step 23 — Reliability science v2 — complete

Added a frozen model-free cross-component reliability v2 suite covering
routing, multi-file repository inspection, workflows, structured data,
visual-document evidence, memory isolation/expiry, prompt injection, research
denial, quantum, and optimization, with repeated trials, Wilson intervals, and
failure taxonomies. Model-backed statistical trials remain an additional
evaluation stratum.

### Step 24 — Performance engineering — complete

Added trace-friendly service measurements for cold/warm health, workflows,
library, routing, disk, platform, and peak process memory. Token, model-swap,
host-level unified-memory, and concurrency collectors remain measurement
expansions; optimize only from traces.

### Step 25 — Packaging and release engineering — complete

Added a package-readiness check, one supported editable-install path,
`atelier init`, runtime-home validation/repair, model setup guidance,
runtime export/restore, macOS smoke CI, Finder action documentation, and
incremental release tags. Protected-master settings were verified read-only;
full schema migration automation and signed artifacts remain release
extensions.

### Step 26 — Atelier v1.0 acceptance — complete locally

Added `atelier acceptance` and `atelier acceptance --clean` to verify the
deterministic clean-Mac foundation, then completed the isolated local
model-backed scenario: fresh runtime initialization, workspace attachment,
paper ingestion and characterization, cited Qwen3-8B answering, test-verified
repository modification, structured-data profiling, figure evidence, quantum
and optimization tools, project memory, `LOCAL_ONLY` denial, handoff creation,
shared CLI/UI service coverage, restart/recovery, and reliability/security/
performance gates. Evidence is recorded in
[`archive/steps/STEP_26_ATELIER_V1_RELEASE.md`](archive/steps/STEP_26_ATELIER_V1_RELEASE.md).

The local release does not claim provider-backed quantum execution, external
solver availability, kernel-level isolation, signed artifacts, automatic cloud
routing, or live frontier handoffs. Those remain explicit future extensions.

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

The Tier C expert slot is reserved for the upcoming Qwen3.8-27B release. It is
an evaluation-only slot: download one Q4-class candidate, benchmark research
reasoning, document QA, coding, and UPSC preparation, and promote it only if
the quality and memory results justify replacing the temporary Qwen3-8B brain.
