# Current Atelier Architecture

Status: **Atelier v1.0 verified locally; optional extensions remain**

## Shipped baseline

- CLI, persistent session, and MCP server share one application/tool registry.
- Local reasoning uses Ollama; the installed heavy fallback is `gemma4:26b`.
- The installed worker is LFM2.5-2.6B Q6_K.
- Retrieval uses `qwen3-embedding:4b` at 2,560 dimensions.
- ChromaDB stores vectors; SQLite stores document and compatibility manifests.
- PDF extraction is content-addressed, cached, and section-aware.
- Hybrid retrieval combines dense search, BM25, RRF, section adjustment, and
  deterministic diversity.
- Semantic memory has backup-backed migration and a separate collection.
- Root and agent dependencies are declared; Linux CI runs the full suite.
- `master` is protected and requires the `Python 3.11` Test workflow.
- Workspace roots are persisted with read/write/execute/network capabilities;
  `LOCAL_ONLY` is the default privacy policy.
- Agent, MCP, and CLI tool dispatch receive an explicit workspace context.
- Deterministic repository inspection reports Git, languages, environments,
  tests, entry points, symbols, imports, test links, and important files.
- A dedicated `coder` role uses `qwen3:8b`, selected through a frozen
  multi-file benchmark with test-pass, tool-use, latency, memory, and token
  measurements.
- `atelier code-fix` wraps the ReAct primitive in a typed build workflow with
  deterministic inspection, baseline/regression tests, checkpoints, optional
  escalation to the brain, diff review, rollback, and a JSON certificate.
- Capability-first routing and a role-aware model lifecycle registry expose
  `atelier route`, `atelier models list`, `atelier models status`, and
  `atelier models bench`.
- PDF visual evidence and deterministic `ArtifactProfile` adapters precede
  model reasoning for scientific documents and structured files.
- Explicit network research lookup records provenance and is denied under
  `LOCAL_ONLY` or without an attached network-capable workspace.
- Research lookup responses are cached under the external runtime home;
  related/cited-by discovery, Crossref citation verification, and allowlisted
  paper downloads with SHA-256 sidecars are available as explicit operations.
- OpenQASM/Qiskit-aware circuit inspection and deterministic optimization
  feasibility/objective checks are exposed as agent tools.
- Small OpenQASM circuits can be simulated with a bounded NumPy statevector;
  small LPs use SciPy HiGHS when available, binary QUBOs use exact local
  enumeration, and explicit candidate solutions can be compared.
- Typed workflow specifications now have a durable JSON execution engine with
  per-step checkpoints, approval pauses, recovery, cancellation, and shared
  service/API task operations. Project/session memory integration and
  expiration enforcement are covered by the project-memory store.
- Project memory now enforces expiry, records structured provenance, and stores
  isolated session/task/artifact entities; workflow tasks are mirrored into
  that project state.
- Registry dispatch applies shell allowlists, secret redaction, untrusted
  output markers, and minimal audit events through a security boundary.
- `atelier.service.AtelierService` and the loopback `atelier serve` API provide
  shared JSON-friendly operations for CLI/UI clients, including chat/task
  routing, source viewing, bounded uploads, paper/repository actions, and
  workflow approvals.
- The loopback web workbench exposes workspace/privacy, library, models,
  workflows, chat, search, source viewing, uploads, paper actions, repository
  actions, and approval buttons through that service.
- A versioned external runtime-home layout is active by default under
  `~/Atelier`; state migration is copy-first, source-preserving, and
  record-scoped for rollback. The migrated three-paper index is currently
  verified at 223 chunks with Qwen3-Embedding-4B / 2,560 dimensions.

## Deliberate placeholders

`qwen3:14b` remains the default brain configuration and `qwen3:4b` remains the
router configuration, but neither is installed. These are benchmark decisions,
not setup failures. The project will choose future coding, routing, and vision
models through frozen evaluations rather than by accumulating downloads.

## Remaining roadmap work

- broader research-source coverage beyond the current Crossref/arXiv/Semantic
  Scholar operations;
- richer quantum transpilation and provider-backed backend comparison;
- broader hardened security isolation beyond the current capability boundary,
  prompt-injection markers, secret redaction, one-use destructive confirmations,
  and audit logging;
- polished web trace/source rendering and richer selected-context presentation;
- external solver integrations, hardened OS-level isolation, signed artifacts,
  automatic cloud routing, and richer frontier handoffs.

The dependency-ordered roadmap for these capabilities is maintained in
[`ATELIER_WORKBENCH_PLAN.md`](ATELIER_WORKBENCH_PLAN.md).
