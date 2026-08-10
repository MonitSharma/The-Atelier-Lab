# Steps 13–16 — Research, scientific tools, workflows, and project memory

Status: **complete on the current development line**

## Step 13 — Explicit research lookup

`tools.research` exposes `research_lookup` for explicit metadata queries to
Crossref, arXiv, and Semantic Scholar. Each result records its source, query
or DOI, retrieval timestamp, request endpoint, and normalized records.

The tool does not accept local file contents. It requires an active Atelier
workspace with both `network` capability and `CLOUD_ALLOWED` privacy. A
`LOCAL_ONLY` workspace returns a structured denial before opening a socket.

Example setup and use:

```bash
atelier workspace add ~/research --name research-net \
  --capabilities read,network --privacy CLOUD_ALLOWED
atelier workspace open research-net
atelier research-lookup "quantum approximate optimization" --source arxiv
```

The agent-facing tool is available through the same registry as local tools.
Downloads remain a separately gated operation, while explicit paper ingestion
is available through the local library workflow. Downloaded results carry a
SHA-256/timestamp/URL provenance sidecar under an approved workspace.

## Step 14 — Quantum and optimization checks

`quantum_inspect` parses OpenQASM deterministically. When Qiskit is installed,
it reports Qiskit circuit depth, qubit/classical-bit counts, measurements, and
operation counts. Without Qiskit, the current environment uses a clearly
labelled OpenQASM 2 minimal parser and reports that depth is a conservative
gate-count estimate. No backend is contacted and no circuit is executed by
the fallback.

Install the optional Qiskit capability only when the project needs it:

```bash
uv pip install -e '.[quantum]'
atelier quantum inspect --path circuit.qasm
atelier quantum transpile --path circuit.qasm
```

`quantum_transpile` exposes optional Qiskit transpilation with an explicit
dependency-unavailable result when Qiskit is absent. `quantum_compare_backends`
compares resources against caller-supplied provider-free capacity profiles and
never contacts a backend.

`optimization_validate` checks an explicit LP/QUBO-style candidate: objective
value, linear constraints, variable bounds, relation satisfaction, and final
feasibility. It returns failed checks rather than mutating a problem or
claiming that a solver found a solution. SciPy is already available for a
future solver-backed extension.

## Step 15 — Explicit workflows

`atelier workflows` exposes typed specifications for `paper_fast`,
`paper_deep_read`, `paper_compare`, `repo_inspect`, `code_fix`, `data_analyze`,
`research_verify`, `quantum_analyze`, and `optimization_validate`. Each
specification declares ordered steps, required capabilities, an approval gate,
and recovery behavior. The catalog is deliberately separate from execution so
the backend and UI share the same visible workflow contract. The durable JSON
engine now persists checkpoints, pauses for approvals, and supports recovery
and cancellation.

## Step 16 — Project memory v2

`agent.project_memory.ProjectMemoryStore` is a separate SQLite store for
explicit project-scoped items. Supported kinds are durable user facts, task
state, source notes, project notes, artifacts, and decisions. Each item can
carry a source and optional expiry.

```bash
atelier project memory-add atelier "Qwen3 8B is the selected coder" \
  --kind decision --source docs/archive/steps/STEP_07_CODING_SPECIALIST_BENCHMARK.md
atelier project memory-list atelier
atelier project memory-export atelier /tmp/atelier-memory.json
atelier project memory-import atelier /tmp/atelier-memory.json
atelier project memory-forget atelier MEMORY_ID
```

Project namespaces are enforced in list and forget operations, and imports
rewrite the destination namespace instead of trusting the source namespace.
Conversation transcripts are not automatically stored. The existing semantic
user-memory system remains available separately for durable facts and recall;
workflow task state is mirrored into project entities with provenance.

## Verification

Focused tests cover network denial and provenance, deterministic QASM fallback,
feasibility and objective checks, project isolation/export/import, workflow
metadata, and tool registration. The full test suite is the merge gate.
