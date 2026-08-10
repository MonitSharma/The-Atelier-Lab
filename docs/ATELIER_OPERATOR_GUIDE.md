# Atelier Operator Guide

This is the practical guide to the current Atelier release. It explains what
the system does, how to run it, how data moves through it, which models are
installed, and what each model is responsible for.

The active implementation lives in
[`atelier_agent/`](../atelier_agent/). User data and runtime state live outside
the Git checkout under `~/Atelier`, so updating the code does not overwrite the
research library, vector index, memory, traces, or workflow state.

## 1. What Atelier is

Atelier is a local-first research workbench with two primary modes:

- **Knowledge mode:** ingest papers, notes, PDFs, and source code; retrieve
  relevant passages; answer with file/page citations.
- **Build mode:** inspect a repository, plan a change, edit through guarded
  tools, run tests, and return a certificate describing the verified change.

It also provides deterministic artifact profiling, paper/figure evidence,
research provenance, quantum and optimization checks, durable workflows,
project memory, a loopback web UI, MCP access, and explicit handoff planning.

The default privacy policy is `LOCAL_ONLY`. Network research and external
handoffs require explicit workspace capabilities and user approval.

## 2. Quick start on this Mac

```bash
cd ~/code_projects/The-Atelier-Lab/atelier_agent
source ../.venv/bin/activate

# Confirm the local runtime and model installation.
atelier doctor
atelier models status

# Attach a project explicitly. Use the smallest appropriate capability set.
atelier workspace add ~/code_projects/my-project \
  --name my-project --capabilities read,write,execute
atelier workspace open my-project

# Index local research material.
atelier ingest ~/Documents/papers ./Project.md
atelier sources

# Search first, then ask for a grounded synthesis.
atelier search "quantum advantage in the indexed papers"
atelier ask --show-context "What is the strongest evidence for quantum advantage?"

# Inspect and repair code with tests.
atelier repo inspect ~/code_projects/my-project
atelier code-fix "Fix the failing tests and return a verified certificate" \
  --path ~/code_projects/my-project --no-escalate --json
```

Run `atelier --help` or `atelier COMMAND --help` for the complete option set.

## 3. Common workflows

### Research and paper analysis

```bash
atelier paper ~/Documents/papers/paper.pdf --ingest
atelier paper-visual ~/Documents/papers/paper.pdf --render --json
atelier search "regret bound under stochastic demand"
atelier ask -k 8 --show-context "Summarize the method and limitations."
atelier research graph "quantum logistics tail risk"
atelier research verify-citation --doi 10.xxxx/example
```

`paper` performs deterministic identity, extraction, and characterization.
`paper-visual` records page evidence, captions, tables, rendered images, and
optional OCR status. Model reasoning happens after evidence preparation.

### Repository exploration and coding

```bash
atelier repo inspect ~/code_projects/my-project
atelier repo status ~/code_projects/my-project
atelier repo symbols ~/code_projects/my-project
atelier repo tests ~/code_projects/my-project
atelier repo search "TODO|FIXME" --path ~/code_projects/my-project

atelier agent "Explain the failing test, fix it, and prove it passes"
atelier code-fix "Add validation and regression tests" \
  --path ~/code_projects/my-project --no-escalate --json
```

The coding workflow follows `inspect → baseline tests → edit → regression tests
→ diff review → certificate`. Generated files such as `.git`, virtualenvs,
cache directories, and `.pyc` files are excluded from the changed-file
certificate.

### Structured data

```bash
atelier profile ~/Documents/data/results.csv --json
atelier profile ~/Documents/data/results.xlsx --json
```

Profiling happens before model reasoning and reports schema, shape, missingness,
formulas, references, warnings, and a bounded preview.

### Memory and durable projects

```bash
atelier remember "I prefer pytest and Apache-2.0" --tags preferences
atelier recall "Which test framework do I prefer?"
atelier memory

atelier project memory-add quantum-project "Use QUBO only when the binary encoding is explicit"
atelier project context quantum-project
atelier project session-start quantum-project
```

Semantic user memory, project memory, workflow tasks, sessions, and artifacts
are separate state types. Conversation text is not automatically promoted to
durable memory.

### Workflows and approvals

```bash
atelier workflows
atelier workflow run paper_deep_read --input paper.json
atelier workflow status RUN_ID
atelier workflow approve RUN_ID
atelier workflow recover RUN_ID
```

Approval-gated steps pause with persisted checkpoints. Restarting Atelier can
reconstruct the service and resume a workflow without losing the prior trace.

### Quantum and optimization tools

```bash
atelier quantum inspect --qasm 'OPENQASM 2.0; qreg q[1]; h q[0];'
atelier quantum simulate --qasm 'OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];'
atelier quantum transpile --qasm 'OPENQASM 2.0; qreg q[1]; h q[0];'
atelier optimize solve problem.json
atelier optimize validate problem.json
```

Small circuits use the bounded local NumPy statevector simulator. Qiskit
transpilation is optional and reports an explicit unavailable result when the
package is not installed. Provider-free backend comparison accepts explicit
capacity profiles; it does not contact a cloud backend.

### Web UI, MCP, and handoffs

```bash
atelier serve                         # loopback UI/API, normally 127.0.0.1:8787
atelier mcp                           # MCP over stdio
atelier finder plan ~/Documents/paper.pdf
atelier handoff create --target codex --task "Review this result"
```

The web UI and CLI use the same `AtelierService`; they do not maintain separate
business logic. Finder actions and handoffs are explicit plans until approved.

## 4. Architecture

```text
CLI / loopback web UI / Finder actions / MCP / persistent session
                              │
                     AtelierService + API
                              │
              workspace context + privacy policy
                              │
       characterize → route → retrieve → tools → reason → verify
             │          │         │          │          │
             │          │         │          │          └─ traces/certificates
             │          │         │          └─ guarded shared registry
             │          │         └─ Chroma dense + BM25 + RRF retrieval
             │          └─ capability router + model lifecycle registry
             └─ PDF/artifact/figure evidence before synthesis
                              │
                 Ollama local models or MLX provider
```

### Request path in knowledge mode

1. The workspace manager verifies that the source is approved for `read`.
2. Ingestion assigns content identity and updates the SQLite manifest.
3. PDFs are extracted and chunked with page/section metadata.
4. Qwen3-Embedding-4B creates 2,560-dimensional vectors in ChromaDB.
5. Dense retrieval and BM25 lexical retrieval are fused with reciprocal-rank
   fusion, section adjustment, and diversity controls.
6. The selected passages are sent to the chosen local model.
7. The answer includes source/page evidence and records a trace.

### Request path in build mode

1. The workspace manager checks `read`, `write`, and `execute` capabilities.
2. Repository inspection maps Git state, languages, tests, symbols, imports,
   entry points, and important files without model reasoning.
3. The router selects the coding workflow and `coder` role.
4. The ReAct loop emits one typed tool action at a time.
5. Edits are syntax-checked, tests run in a bounded subprocess, and observations
   are capped.
6. The build workflow records checkpoints, reviews the diff, and returns a JSON
   certificate.

### Persistent state

```text
~/Atelier/
├── library/corpus/          source PDFs, notes, and code copies/links
├── library/extracted/       extracted paper text
├── library/paper_metadata/  identity and characterization records
├── databases/vectorstore/   ChromaDB embeddings
├── databases/*sqlite3       manifests, semantic memory, project memory
├── logs/traces/              ReAct traces
├── logs/workflows/           durable workflow checkpoints
├── logs/tool_calls.jsonl     security/audit events
├── cache/                    visual and research caches
├── backups/                  migration and memory backups
└── workspaces/registry.json  approved roots and capabilities
```

The source checkout is code. `~/Atelier` is the working state.

## 5. Model stack and current disk usage

The model registry separates role from model name. A configured model can be
intentionally missing; `atelier models status` reports that state instead of
downloading models automatically.

### Installed models on the current Mac

Sizes below are the current Ollama disk sizes from `ollama list`, not a promise
of exact resident RAM. Resident memory varies with context length and concurrent
models.

| Role / model | Installed size | Approx. memory estimate | Primary job |
|---|---:|---:|---|
| Worker — `hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K` | 2.2 GB | 3 GB | fast extraction, classification, JSON, repetitive RAG tasks |
| Coder — `qwen3:8b` | 5.2 GB | 6 GB | repository edits, tool use, tests, small coding jobs |
| Embeddings — `qwen3-embedding:4b` | 2.5 GB | used by retrieval | document/query vectors, 2,560 dimensions |
| Heavy — `gemma4:26b` | 17 GB | 20 GB | hardest local reasoning and long-context synthesis |
| Optional candidate — `qwen2.5-coder:7b` | 4.7 GB | not selected | alternative coding benchmark candidate |
| Optional candidate — `gemma4:12b-it-q4_K_M` | 7.6 GB | not selected | alternative local reasoning candidate |

Current configured-but-not-installed placeholders:

| Role | Configured model | Purpose |
|---|---|---|
| Brain | `qwen3:14b` | general reasoning and larger build tasks |
| Router target | `qwen3:4b` | future model-backed routing experiment |
| Expert | empty | reserved capability slot |

The fresh local acceptance run used `qwen3:8b` explicitly for both the cited
paper ask and the repository coding workflow. The default configuration still
names `qwen3:14b` as the brain placeholder, so use an explicit override when
you want the installed 8B model:

```bash
export ATELIER_BRAIN_MODEL=qwen3:8b
export ATELIER_CODER_MODEL=qwen3:8b
```

The six installed Ollama models currently occupy roughly 39 GB on disk. The
active external Atelier runtime is about 18 MB because the corpus/index is
already compact and the large model files remain managed by Ollama.

### Four capability tiers

| Tier | Intended role | Current implementation |
|---|---|---|
| A — tiny worker | routing, classification, metadata, query rewriting, JSON | LFM2.5-2.6B Q6_K |
| B — small coding agent | scripts, tests, bug fixes, repository exploration | Qwen3-8B; Qwen2.5-Coder-7B remains a candidate |
| C — main local intelligence | mathematics, papers, optimization, quantum reasoning | Qwen3-14B is configured; Qwen3.8-27B Q4 remains a future hardware-budget decision |
| D — frontier handoffs | architecture, implementation, long context, multimodal review | Claude = critic/architect; Codex = implementation; Gemini = large-context/multimodal |

Do not load the 17 GB heavy model at the same time as every other large model
on a 36 GiB machine. Serialize model-heavy operations and watch
`atelier performance` for peak process memory.

## 6. Privacy and safety rules

- `LOCAL_ONLY` is the default.
- A workspace must explicitly grant `network` before research lookup or paper
  download can run.
- File, execution, repository, and research tools receive workspace context;
  paths outside approved roots are rejected.
- Destructive actions require a one-use confirmation.
- Tool output is marked as untrusted data and prompt-injection patterns are
  recorded rather than followed.
- Frontier handoffs are bundles that remain unapproved until the user permits
  external transfer.
- The application boundary is not a kernel-level sandbox; use a separate OS
  account or container for hostile code.

## 7. Maintenance and verification

```bash
cd ~/code_projects/The-Atelier-Lab/atelier_agent
source ../.venv/bin/activate

atelier doctor
atelier state validate --home ~/Atelier
atelier acceptance
atelier acceptance --clean
atelier route-eval
atelier reliability --suite v2 --repetitions 2
atelier package check
atelier performance
pytest -q
```

The local release evidence is in
[`steps/STEP_26_ATELIER_V1_RELEASE.md`](steps/STEP_26_ATELIER_V1_RELEASE.md).
The dependency-ordered plan is in
[`ATELIER_WORKBENCH_PLAN.md`](ATELIER_WORKBENCH_PLAN.md).

## 8. Repository and branch policy

`master` is the canonical branch because the GitHub repository currently uses
`origin/HEAD → origin/master`. The `codex/...` branches were milestone branches
created while building the system. Their tips are all contained in the verified
v1.0 history and their milestone tags preserve the historical release points.

After consolidation, use this policy:

```text
master                 canonical development/release branch
atelier-v1.0           current local release tag
atelier-*-v1.0         historical milestone tags
codex/*                temporary feature branches; delete after merge
```

Do not delete tags when cleaning branches. Tags are the useful historical
record; feature branch pointers are not.
