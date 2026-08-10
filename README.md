# The Atelier Lab

**A local-first research workbench for one researcher working across papers, documents, code, quantum computing, optimization, and UPSC preparation.**

> How much reliable AI capability can one researcher obtain from local models under fixed memory, latency, privacy, and compute constraints?

Atelier is the operational center of The Atelier Lab. It gives one terminal interface to a local document library, hybrid retrieval, model routing, guarded repository tools, deterministic scientific tools, durable memory, and verification. The default path is deliberately small:

```text
ingest → search / ask → agent or code-fix → verify
```

![Atelier end-to-end workflow](docs/assets/atelier-workflow.svg)

The project also contains a structured learning track for implementing language models from first principles and a reproducible experiment registry for Apple Silicon, local inference, agents, retrieval, and training.

## What Atelier does

| Capability | What it provides |
|---|---|
| Knowledge mode | Ingest and question papers, DOCX, PPTX, spreadsheets, notes, images, EPUBs, archives, and source code |
| Research mode | Page-aware extraction, semantic + lexical retrieval, citations, paper characterization, visual evidence, and research planning |
| UPSC study mode | Grounded revision over the `exam_website` material: Prelims, Mains, current affairs, essays, ethics, CSAT, and optional-subject notes |
| Build mode | Repository inspection, guarded edits, tests, diff review, and a verification certificate |
| Scientific tools | Deterministic quantum-circuit inspection/simulation and optimization validation |
| Memory | Local semantic memory, explicit project memory, workflow checkpoints, traces, and audit logs |
| Interfaces | Responsive terminal CLI, optional loopback web UI, and MCP bridge for compatible external hosts |

Atelier is not intended to replace human judgment in research or examination preparation. Retrieval provides evidence; the user decides whether that evidence is correct, current, and sufficient.

## The interface

The normal entry point is now available from any directory on the Mac:

```bash
atelier
```

The interactive prompt accepts Atelier commands and familiar terminal navigation. `cd` changes the active workspace, `ls`, `find`, `rg`, `git`, and `cat` work inside the session, and `Tab` completes commands and nested filesystem paths. The display refreshes to the current Terminal width, including after maximizing or resizing the window.

![Illustrative Atelier terminal interface](docs/assets/atelier-interface.svg)

Typical session:

```text
atelier › cd ~/Downloads
atelier › ingest QAtelier_Quantum_Adapters_Research_Plan.docx
atelier › search "falsifiers and hardware validation"
atelier › ask --show-context "What evidence is required before claiming quantum advantage?"
atelier › exit
```

Use `help` for the daily commands and `advanced-help` only when you need services, evaluation, research, quantum, optimization, or workflow commands. `Ctrl-C` cancels a child operation and leaves the Atelier prompt open; `exit` closes the session.

## Quick start

### Use the installed launcher

```bash
atelier doctor
atelier models status
atelier
```

The launcher uses the project’s editable virtual environment, so normal use does not require activating a venv. User documents and runtime state are stored outside the repository under `~/Atelier`.

### Install from a fresh checkout

```bash
git clone https://github.com/MonitSharma/The-Atelier-Lab.git
cd The-Atelier-Lab
uv venv atelier_agent/.venv
uv pip install -r atelier_agent/requirements.txt
uv pip install -e atelier_agent
atelier doctor
```

For development checks:

```bash
make -C atelier_agent test
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
```

## Worked examples

### 1. Understand the QAtelier research plan

Start with a text-first pass, then ask progressively more specific questions:

```bash
atelier
```

```text
atelier › ingest ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
atelier › sources
atelier › search "central question proposed contribution and falsifiers"
atelier › ask --show-context "Summarize the objective, hypothesis, method, baselines, metrics, and risks."
atelier › ask "Separate explicit assumptions from recommendations and open questions."
atelier › ask "What should I implement or test first, and what result would falsify the main claim?"
```

`--show-context` is the inspection mode: it shows the passages supplied to the model, with headings, pages, tables, slides, image members, archive members, and human-review flags where available. The answer is grounded in those passages and cites them, but important equations, tables, OCR, and claims still require manual verification.

For layout-dependent equations or figures, also export a PDF and use:

```text
atelier › paper ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.pdf --ingest
atelier › paper-visual ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.pdf --json
```

### 2. Prepare for UPSC

The agent is a general research and study workbench, not only a coding tool. Index the preparation material once, then ask for source-grounded revision:

```text
atelier › cd ~/code_projects/exam_website
atelier › ingest .
atelier › sources
atelier › ask --show-context "Create a 10-question Prelims quiz on wetlands from the indexed material."
atelier › ask "Compare the constitutional provisions in these notes and flag claims that need current verification."
atelier › ask "Turn this week’s current-affairs notes into a revision sheet with facts, links, PYQ connections, and likely traps."
```

For Mains, ask for an answer structure rather than an unsupported final answer:

```text
atelier › ask "Draft a 250-word GS answer using only the indexed notes. Separate facts, examples, arguments, and limitations, and cite the source files."
```

The UPSC workflow is documented in [`docs/UPSC_PREPARATION_TRACK.md`](docs/UPSC_PREPARATION_TRACK.md).

### 3. Explore and modify a repository

Use deterministic inspection before asking a model to edit anything:

```bash
atelier --workspace ~/code_projects/The-Atelier-Lab repo inspect .
atelier --workspace ~/code_projects/The-Atelier-Lab repo tests .
atelier --workspace ~/code_projects/The-Atelier-Lab agent \
  "Find the smallest safe fix for the failing tests, implement it, run the relevant tests, and explain the evidence."
```

For a more constrained change:

```bash
atelier code-fix "Add regression coverage for nested path completion" \
  --path ~/code_projects/The-Atelier-Lab --no-escalate --json
```

Build mode follows:

```text
inspect → baseline tests → edit → regression tests → diff review → certificate
```

Workspace capabilities are explicit. `read` is enough for inspection; `write` and `execute` are required for modifications and tests. The default privacy policy is `LOCAL_ONLY`.

### 4. Read handwritten notes and images

Modern images are treated as evidence inputs rather than opaque attachments:

```text
atelier › ingest ~/Downloads/handwritten-note.png
atelier › ask "Transcribe the legible content, preserve headings, and mark uncertain words or equations for human review."
```

Supported image types include PNG, JPG, TIFF, WEBP, and BMP. Atelier combines local Tesseract OCR with the installed local vision model when available. OCR confidence, vision confidence, and review flags remain attached to retrieved context.

### 5. Inspect a quantum or optimization artifact

These commands are deterministic and do not require a frontier model:

```bash
atelier quantum inspect --qasm 'OPENQASM 2.0; qreg q[1]; h q[0];'
atelier quantum simulate --qasm 'OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];'
atelier optimize validate problem.json
```

The quantum simulator is a bounded local NumPy statevector tool. Optional Qiskit support reports an explicit unavailable result when Qiskit is not installed; no cloud backend is contacted by these commands.

## Supported material

| Input | Local handling |
|---|---|
| PDF | Page-aware extraction, paper metadata, page citations, and OCR fallback for image-only pages |
| DOCX | Heading-aware paragraphs, tables, embedded images, and image locations |
| PPTX | Slide text, speaker notes, embedded images, and slide citations |
| XLSX / XLSM | Visible cell values, bounded previews, formulas/references where available |
| Markdown, text, HTML, RTF, TeX, JSON, CSV/TSV, notebooks, source code | Local text extraction and retrieval chunks |
| EPUB | HTML/XHTML chapter text |
| PNG, JPG, TIFF, WEBP, BMP | Tesseract OCR plus local vision descriptions for handwriting, diagrams, and equations |
| ZIP | Recursive, non-executing ingestion of supported members with strict security limits and archive-member citations |

Old binary Office formats (`.doc`, `.ppt`, `.xls`), encrypted files, arbitrary binaries, and visually ambiguous content require conversion or human review. Atelier never executes files extracted from archives.

## Architecture

Atelier has one service contract behind the CLI, optional web UI, persistent session, and MCP bridge. The principal knowledge path is:

1. The workspace manager confirms the source path and capability boundary.
2. Ingestion assigns content identity, extracts structure, and writes the SQLite manifest.
3. PDFs, Office files, images, EPUBs, archives, and code become citation-aware chunks.
4. Qwen3-Embedding-4B creates 2,560-dimensional local vectors in ChromaDB.
5. Dense retrieval and BM25 lexical retrieval are fused with reciprocal-rank fusion, section adjustment, and diversity controls.
6. The selected passages are sent to the appropriate local model role.
7. The response returns citations and records traces, review flags, and workflow state where applicable.

Build mode follows a parallel evidence path: deterministic repository inspection → capability routing → guarded tool calls → bounded tests → diff review → certificate.

### Runtime state

The Git checkout contains code and reproducible fixtures. User data lives outside it:

```text
~/Atelier/
├── library/corpus/          ingested source material
├── library/extracted/       extracted paper/document text
├── library/paper_metadata/  paper identity and characterization
├── databases/vectorstore/   ChromaDB embeddings
├── databases/*sqlite3       manifests and memory stores
├── logs/traces/              agent traces
├── logs/workflows/           durable workflow checkpoints
├── logs/tool_calls.jsonl     audit events
├── cache/                    visual and research caches
├── backups/                  migration and memory backups
└── workspaces/registry.json  approved roots and capabilities
```

This separation means updating the repository does not overwrite the research library, vector index, memory, traces, or workflow state.

### `serve` and `mcp`

These are optional integration surfaces, not daily commands:

```bash
atelier serve   # loopback web/API at http://127.0.0.1:8787/ui
atelier mcp     # JSON-RPC bridge launched by a compatible MCP host
```

Run `serve` in a separate terminal. `mcp` intentionally waits for protocol messages on stdin and may look idle when launched manually; configure Claude Desktop/Code or another MCP-compatible host to launch it. Both use the same `AtelierService` as the CLI.

## Model stack

The stack is capability-first: no model is downloaded merely because it is interesting. A role must have a clear consumer, a memory budget, and an evaluation.

![Atelier model tiers](docs/assets/atelier-model-stack.svg)

### Current local inventory

Measured from `ollama list` on **10 August 2026**. Disk size is Ollama storage, not a guarantee of resident memory. The heavy and vision roles share one `gemma4:26b` model file.

| Role | Model | Ollama size | Purpose |
|---|---|---:|---|
| Worker | `hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K` | 2.2 GB | routing, classification, metadata extraction, query rewriting, JSON, repetitive RAG |
| Brain | `qwen3:8b` | 5.2 GB | normal local reasoning, study questions, synthesis, agent planning |
| Coder | `qwen3:8b` | 5.2 GB | repository exploration, scripts, small fixes, tests, refactoring |
| Embeddings | `qwen3-embedding:4b` | 2.5 GB | local semantic retrieval; 2,560-dimensional vectors |
| Heavy + vision | `gemma4:26b` | 17 GB | difficult synthesis, long-context reasoning, handwriting, diagrams, equations, embedded images |
| Candidate | `qwen2.5-coder:7b` | 4.7 GB | alternative coding benchmark; not selected as the active coder |
| Candidate | `gemma4:12b-it-q4_K_M` | 7.6 GB | alternative local reasoning candidate; not selected as the active brain |

The current Ollama model store occupies approximately **38 GB** on disk. Verify the live state with:

```bash
ollama list
atelier models status
atelier doctor
```

### Four-tier policy

| Tier | Capability | Policy |
|---|---|---|
| A — tiny worker | cheap repetitive decisions | LFM2.5-2.6B is the active candidate |
| B — small coding agent | scripts, tests, bug fixes, repository exploration | Qwen3-8B is active; alternatives are benchmark candidates |
| C — main local intelligence | mathematics, papers, optimization, quantum reasoning, private synthesis | Qwen3.8-27B Q4-class slot reserved for controlled evaluation |
| D — frontier handoffs | architecture, implementation, very large context, multimodal review | Claude = critic/architect; Codex = implementation; Gemini = large context/multimodal |

Qwen3.8-27B is intentionally **not** treated as active until its released tag is known and it passes the evaluation gate: disk/resident-memory behavior, research QA, document QA, coding, UPSC study quality, citation accuracy, latency, and peak memory on this Mac. The temporary brain remains Qwen3-8B until that comparison justifies promotion.

## Hardware and storage budget

The current target is regular local experimentation on the following machine:

| Resource | Current measurement |
|---|---|
| Mac | MacBook Pro, model identifier `Mac15,7` |
| Chip | Apple M3 Pro, 12 cores: 6 performance + 6 efficiency |
| Unified memory | 36 GB |
| Root volume | 460 GiB total; 100 GiB available at the time of this README update |
| Ollama models | approximately 38 GB under `~/.ollama/models` |
| Atelier runtime state | 77 MB under `~/Atelier` at the time of measurement |
| Operating target | keep at least 80–100 GB free before adding a new large local model |

The 25–30B Q4 class is the upper regular-use range targeted for this 36 GB machine. Do not load the 17 GB Gemma model concurrently with multiple other large models. Serialize heavy reasoning, vision, embedding migrations, and future Qwen3.8-27B evaluation when necessary, and record peak memory rather than relying on model file size alone.

Storage commands:

```bash
df -h /
du -sh ~/.ollama/models ~/Atelier
ollama list
```

The external Google Drive archive is useful for cold project material and backups; the active index, models, and frequently used documents remain local for latency and predictable privacy. Moving files to Drive does not automatically add them to Atelier’s local index.

## Privacy and safety

- `LOCAL_ONLY` is the default privacy policy.
- Ingested files, vectors, memory, traces, and model calls remain local by default.
- Workspace capabilities distinguish `read`, `write`, `execute`, and `network`.
- Research lookup, downloads, and frontier handoffs require explicit approval.
- Destructive operations require a one-use confirmation.
- ZIP ingestion is non-executing and bounded by depth, member count, size, path, encryption, and compression-ratio checks.
- OCR and vision are extraction aids, not proof. Low-confidence text, handwriting, equations, figures, and current-affairs claims require human review.

## Project tracks

- **Foundations:** tensors, probability, tokenization, language modelling, attention, transformers, training, and inference.
- **Local AI systems:** Apple Silicon performance, quantization, KV caching, memory, serving, and routing.
- **Reliable agents:** RAG, tools, code modification, verification, memory, routing, and evaluation.
- **Research domains:** AI, quantum computing, optimization, mathematics, operations research, and scientific computing.
- **UPSC preparation:** Prelims, Mains, CSAT, current affairs, essays, ethics, geography, polity, economy, environment, history, and optional-subject material.

## Measured results

The latest committed expanded suites record **17/18 knowledge answers**, **13/13 code tasks**, and **10/10 combined tasks** solved. These are small, mostly single-file evaluation suites and do not establish repository-scale reliability.

The local inference experiment measured Q4_K_M decode rates of **39.3 tok/s for `qwen3:4b`**, **11.5 tok/s for `qwen3:14b`**, and **27.9 tok/s for `gemma4:26b`** on an M3 Pro 36 GB machine. Parameter count alone does not predict speed; architecture and kernels matter.

See [`docs/CURRENT_RESULTS.md`](docs/CURRENT_RESULTS.md) and [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) for the evidence and its boundaries.

## Repository map

```text
The-Atelier-Lab/
├── atelier_agent/       installable CLI, RAG, agent, tools, services, tests
├── foundation/          educational minillm and historical training experiments
├── learning/            numbered language-model learning path
├── experiments/         experiment templates and registry
├── research/            QAtelier research material and experiment notes
├── docs/                user, operator, architecture, UPSC, and research guides
├── scripts/              repository and experiment validation
└── Makefile             project-level checks
```

The canonical branch is `master`. Historical milestone tags are retained; temporary feature branches are merged and deleted.

## Documentation

- [`docs/START_HERE.md`](docs/START_HERE.md) — choose a learning, Atelier, QAtelier, or experiment path.
- [`docs/ATELIER_USER_GUIDE.md`](docs/ATELIER_USER_GUIDE.md) — daily commands and worked workflows.
- [`docs/ATELIER_OPERATOR_GUIDE.md`](docs/ATELIER_OPERATOR_GUIDE.md) — complete runtime, architecture, model, memory, and maintenance guide.
- [`docs/WORKING_WITH_DOCUMENTS.md`](docs/WORKING_WITH_DOCUMENTS.md) — supported formats, OCR, DOCX/PPTX, archives, and document workflow.
- [`docs/UPSC_PREPARATION_TRACK.md`](docs/UPSC_PREPARATION_TRACK.md) — study-specific prompts, evaluation, and the `exam_website` workflow.
- [`docs/CURRENT_ARCHITECTURE.md`](docs/CURRENT_ARCHITECTURE.md) — frozen current-state architecture.
- [`docs/ATELIER_WORKBENCH_PLAN.md`](docs/ATELIER_WORKBENCH_PLAN.md) — phased project plan.
- [`docs/RESEARCH_METHOD.md`](docs/RESEARCH_METHOD.md) — how experiments and negative results are recorded.
- [`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) — detailed source-tree orientation.

## License

The Atelier Lab is released under the Apache License 2.0. See [`atelier_agent/pyproject.toml`](atelier_agent/pyproject.toml) for the package metadata.
