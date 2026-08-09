# Current Atelier Architecture

Status: **post-Scientific Library v1.0; coder benchmark frozen**

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
- OpenQASM/Qiskit-aware circuit inspection and deterministic optimization
  feasibility/objective checks are exposed as agent tools.
- Typed workflow specifications and isolated project memory v2 expose steps,
  approvals, recovery, provenance, expiration, and export/import.
- Registry dispatch applies shell allowlists, secret redaction, untrusted
  output markers, and minimal audit events through a security boundary.
- `atelier.service.AtelierService` and the loopback `atelier serve` API provide
  shared JSON-friendly operations for CLI/UI clients.
- A versioned external runtime-home layout can be initialized and validated;
  state migration is copy-first and record-scoped for rollback.

## Deliberate placeholders

`qwen3:14b` remains the default brain configuration and `qwen3:4b` remains the
router configuration, but neither is installed. These are benchmark decisions,
not setup failures. The project will choose future coding, routing, and vision
models through frozen evaluations rather than by accumulating downloads.

## Not shipped yet

- workflow execution state and hardened approval/daemon boundary;
- web/Finder interfaces and handoffs; external-home activation is the remaining
  packaging/configuration step.

The dependency-ordered roadmap for these capabilities is maintained in
[`ATELIER_WORKBENCH_PLAN.md`](ATELIER_WORKBENCH_PLAN.md).
