<div align="center">

# Project Atelier

**A fully local, zero-cost, dual-mode AI agent that runs on a single MacBook.**

*Answer questions over your own notes. Read and fix your code with test-verified changes.
No cloud, no API keys, no subscriptions — your data never leaves the machine.*

</div>

---

Atelier is one agent harness with **two capability modes**:

- 🧠 **Knowledge mode** — retrieval-augmented Q&A grounded in *your own* notes, PDFs, and code.
- 🔧 **Build mode** — an autonomous agent that reads a repo, edits code, runs tests, and fixes failures, **proving** each change with a green test run.

It runs entirely against a local [Ollama](https://ollama.com) server and local
embedding models. It also ships persistent **memory**, an **MCP server** so other
tools can use its toolbox, **hybrid retrieval**, a **LoRA-fine-tuned router** that
sends easy work to a cheap model, and a **self-evaluation harness** that measures
its own reliability — and reports where it fails.

> **Why local-only?** The research question this project answers is *"how far can a
> fully local, $0 agent go on one laptop?"* The constraints are the point, not a
> limitation. Privacy is a free side effect: nothing is ever sent to a third party.

**Current state:** Phases 0-7 are complete. The project now has an installable
CLI, a local RAG system, an autonomous build-mode agent, durable memory, MCP
tool serving, hybrid retrieval, a fine-tuned router, trace logging, and an
expanded reliability suite: **18 doc-QA tasks**, **13 code-repair tasks**, and
**10 combined knowledge → build tasks** stratified by category, difficulty, and
edit scope.

---

## Table of contents

1. [Highlights](#highlights)
2. [How it works (architecture)](#how-it-works-architecture)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [5-minute quickstart](#5-minute-quickstart)
6. [What's been built — the phases](#whats-been-built--the-phases)
7. [Usage guide](#usage-guide)
   - [Knowledge mode](#knowledge-mode)
   - [Build mode (the agent)](#build-mode-the-agent)
   - [Memory](#memory)
   - [Routing](#routing)
   - [MCP server](#mcp-server)
   - [Evaluation](#evaluation)
8. [CLI command reference](#cli-command-reference)
9. [Configuration reference](#configuration-reference)
10. [Models & hardware budget](#models--hardware-budget)
11. [Reliability results](#reliability-results)
12. [Reproduce everything](#reproduce-everything)
13. [Testing](#testing)
14. [Project structure](#project-structure)
15. [Troubleshooting](#troubleshooting)
16. [Limitations (read these)](#limitations-read-these)
17. [Further reading](#further-reading)
18. [License](#license)

---

## Highlights

| | Feature | What it gives you |
|---|---|---|
| 🧠 | **Grounded Q&A** | Answers cite *your* documents; says "not in your notes" instead of hallucinating |
| 🔧 | **Autonomous coding** | Fixes a failing test across a multi-step tool-using run, verified by pytest |
| 🔎 | **Hybrid retrieval** | Dense (embeddings) + BM25 fused via RRF, with optional cross-encoder reranking |
| 🧩 | **Persistent memory** | Remembers facts/preferences across sessions (semantic recall) |
| 🛰️ | **MCP server** | Exposes its toolbox to Claude Desktop/Code or any MCP host |
| ⚡ | **Fine-tuned router** | A 1-min LoRA fine-tune of a 0.5B model cuts brain calls ~50% with no accuracy loss |
| 📊 | **Self-evaluation** | 18 doc-QA tasks + 13 code tasks + 10 combined tasks, grouped metrics, regression gate, honest reliability numbers |
| 🔒 | **100% local & free** | Only network use: the local Ollama endpoint + one-time model downloads |

---

## How it works (architecture)

```
        you ──▶  atelier CLI  (ask · agent · remember · route · eval · mcp · …)
                      │
        knowledge ────┼──── build / general
            │                     │
            ▼                     ▼
   rag.answer (grounded QA)   agent.react  ── reason → act → observe → repeat
            │                     │  (JSON tool calls, reflection, trace logging)
            ▼                     ▼
   rag.retrieve            tools.registry  ── ONE shared toolbox
   dense + BM25 (RRF)            │
   + optional rerank      ┌──────┼───────────────┬─────────────┐
            │             ▼      ▼               ▼             ▼
            ▼        files   code_exec       search_notes   memory
     rag.embed (bge)  edit   (sandboxed)     (RAG tool)    remember/
     rag.store        test_runner            repo_map       recall
     (ChromaDB)            │
            └──────────────┴──▶ agent.brain ──▶ Ollama (qwen3 / gemma)
                                 agent.router ──▶ fine-tuned 0.5B picks model size
```

Everything above runs on-device. Full design notes: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Requirements

- **macOS on Apple Silicon** (built & tested on **M3 Pro, 36 GB**). Other Apple
  Silicon Macs with ≥16 GB should work with smaller models.
- **[Ollama](https://ollama.com)** installed and running (`ollama serve`).
- **Python 3.11+** and **[`uv`](https://github.com/astral-sh/uv)**.
- ~5 GB free disk for models (more if you add the heavy model).

The local models Atelier uses by role:

```bash
ollama pull qwen3:14b    # "brain"  — reasoning + build mode (default)
ollama pull qwen3:4b     # "worker" — fast/cheap subtasks + the LLM judge
ollama pull gemma4:26b   # "heavy"  — optional, for the hardest reasoning (--heavy)
```

Embedding and router models download automatically from Hugging Face on first use
(`bge-base-en-v1.5` ~110 MB; the 0.5B router base ~300 MB; optional reranker ~80 MB).

---

## Installation

```bash
git clone <your-repo-url> atelier && cd atelier

uv venv && source .venv/bin/activate
uv pip install -r requirements.txt     # pinned, reproducible deps
uv pip install -e .                     # installs the `atelier` command

atelier doctor                          # verify models + vector store + embeddings
```

`atelier doctor` should show all three models green. If one is red, run the
`ollama pull` it prints.

> **No banner in scripts?** Set `ATELIER_NO_BANNER=1` to suppress the ASCII banner.

---

## 5-minute quickstart

```bash
# 1) Index some notes (point it at anything — an Obsidian vault, a papers folder)
atelier ingest ~/Notes ./Project.md

# 2) Ask a question grounded in what you indexed
atelier ask "What did I decide about the embedding model and why?"

# 3) Let the agent fix a bug and prove it with tests
atelier agent "Fix the failing test in sample_task/ and prove it passes"

# 4) Teach it something it will remember next session
atelier remember "I prefer Apache-2.0 and pytest" --tags prefs
atelier recall "what license do I like?"
```

---

## What's been built — the phases

Atelier was built in eight phases (0–7); **all are complete**. Each shipped a
working capability and is verified by tests and/or the eval harness. The
authoritative log lives in [`PROJECT.md`](PROJECT.md) (Decision Log + Changelog).

| Phase | Title | What it delivered | Where |
|---|---|---|---|
| **0** | The loop, from scratch | A hand-written ReAct loop (perceive→plan→act→observe), a local Ollama client, and one verifiable tool (an AST-sandboxed calculator). | `agent/loop.py`, `agent/brain.py`, `tools/calculator.py` |
| **1** | Tools & the protocol | A `Tool`/`ToolRegistry` abstraction and the full toolbox: file read/write/edit + AST edits (workspace-sandboxed), local search, repo map, **sandboxed code execution**, a **pytest runner**, plus an **MCP server** publishing them all. | `tools/`, `atelier/mcp_server.py` |
| **2** | Knowledge mode (RAG) | Ingest (md/txt/pdf/code) → heading-aware chunking → local embeddings → ChromaDB → retrieval → **grounded, cited answers**. | `rag/` |
| **3** | Memory & state | Persistent, semantic long-term memory in its own vector collection; `remember`/`recall` as both CLI commands and agent tools; cross-session persistence. | `agent/memory.py`, `tools/memory_tools.py` |
| **4** | Build mode + reliability | A registry-driven ReAct engine with **reflection** (recovers from tool/parse errors), observation capping, and full **trace logging**. Verified live: the agent fixes a failing test and proves it. | `agent/react.py` |
| **5** | Evaluation & reliability | Two **frozen** task suites (doc-QA + code), deterministic metrics + an optional local **LLM-as-judge**, a runner with JSON reports, and a **regression gate**. | `eval/` |
| **6** | Specialization (routing) | A **LoRA-fine-tuned 0.5B** difficulty classifier routes easy tasks to the cheap model; measured savings. | `models/router/`, `agent/router.py` |
| **7** | Capstone & release | **One-command reproduction** (`make reproduce`), a public **writeup with a figure** and honest failure analysis, and full architecture docs. | `Makefile`, `scripts/`, `docs/` |

Beyond the phases, two engineering improvements were driven *by* the eval (not
guessed): the file-edit tools now run a Python `compile()` check and report
`syntax_ok` so the agent knows instantly when an edit breaks a file; and the
brain client handles `qwen3` "thinking" traces and JSON-mode tool calls robustly.

---

## Usage guide

All commands assume the venv is active (`source .venv/bin/activate`).

### Knowledge mode

```bash
# Index files or whole folders (md, txt, pdf, and source code are supported)
atelier ingest ~/Notes ~/Papers ./Project.md
atelier ingest --reset ~/Notes          # rebuild the index from scratch
atelier sources                          # list what's currently indexed

# Ask, grounded in your corpus
atelier ask "Which embedding model did I choose and why?"
atelier ask -k 8 --show-context "what is build mode's verifier?"   # more context + show passages
atelier ask --heavy "summarize my design decisions"                # use the bigger model

# Interactive session
atelier chat
```

Answers cite sources as `[1] [2]` and list the files used. If the corpus doesn't
contain the answer, the agent says so rather than inventing one — that's by design
and is what the eval's *groundedness* checks measure.

### Build mode (the agent)

```bash
atelier tools                            # list the toolbox the agent can use

# Autonomous, test-verified coding
atelier agent "Fix the failing test in sample_task/ and prove it passes"

# Knowledge + build in one task
atelier agent "Using my notes on X, implement Y in this repo and add a test"
```

Flags:

| Flag | Effect |
|---|---|
| `--heavy` | Use `gemma4:26b` instead of `qwen3:14b` |
| `--memory` | Recall relevant long-term memories into context first |
| `--shell` | Enable the powerful (lightly guarded) `shell` tool |
| `--max-steps N` | Bound the reasoning loop (default 10) |
| `--quiet` | Don't stream each step |

Every run streams its steps and writes a full JSON **trace** to `data/traces/`,
so you can inspect exactly what the agent did.

> **Safety:** file/test tools are pinned to the project workspace; `code_exec`
> runs in a subprocess with a timeout and (on macOS) a seatbelt profile that
> blocks network access. The `shell` tool is opt-in. See
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the exact guarantees.

### Memory

```bash
atelier remember "I prefer Apache-2.0 and pytest over unittest" --tags prefs
atelier recall  "what testing framework does the user like?"
atelier memory                            # list all stored facts
atelier agent --memory "scaffold a module the way I like it"
```

Memory persists across sessions (it lives in a local ChromaDB collection) and is
recalled by **meaning**, not exact words. The agent also has `remember`/`recall`
tools, so it can choose to store facts mid-task.

### Routing

A LoRA-fine-tuned **0.5B** model classifies a task `easy`/`hard` in milliseconds,
so easy subtasks can go to the cheap worker and the 14B brain is reserved for hard
ones (the "small model as a cheap component" pattern).

```bash
atelier route "what is 47 * 89?"                    # easy → qwen3:4b
atelier route "refactor auth across the codebase"   # hard → qwen3:14b
atelier route --backend heuristic "..."             # no model, keyword heuristic

make train-router                                   # reproduce the fine-tune (~1 min)
python -m eval.route_eval                            # measure routing savings
```

If the adapter isn't trained, the router transparently falls back to a keyword
heuristic — nothing depends on the fine-tune at runtime.

### MCP server

Expose Atelier's whole toolbox to any [MCP](https://modelcontextprotocol.io)
client (Claude Desktop/Code, etc.):

```bash
atelier mcp        # speaks JSON-RPC over stdio
```

Point your MCP host's server command at `atelier mcp`. It publishes 12 tools:
`calculator`, `read_file`, `write_file`, `edit_file`, `ast_edit`, `search`,
`search_notes`, `repo_map`, `code_exec`, `test_runner`, `remember`, `recall`
(add `--shell` for the shell tool).

### Evaluation

```bash
atelier eval                  # score both modes, print tables, save a JSON report
atelier eval --mode docqa     # knowledge mode only
atelier eval --mode code      # build mode only
atelier eval --mode combined  # knowledge -> build composition only
atelier eval --judge          # add the local LLM-as-judge (groundedness)
atelier eval --gate           # FAIL (exit 1) if any metric regressed vs the last report
atelier eval-plots            # generate SVG plots from the latest saved report
```

Reports are saved to `data/eval_reports/`. The suites in `eval/tasks_docqa/` and
`eval/tasks_code/` are **frozen on purpose** — add new tasks, don't edit existing
ones, or you invalidate comparisons. The current suite has **18 knowledge-mode
questions**, **13 build-mode code tasks**, and **10 combined knowledge → build
tasks**; report rows include `category`, `difficulty`, and code `edit_scope` so
you can plot success rate by task type. The combined suite counts a task as
solved only if tests pass and the trace used `search_notes`.

`atelier eval-plots` writes dependency-free SVG charts under
`data/eval_reports/plots/<report-name>/`, including overall doc-QA scores,
correctness by doc-QA category, build solved-rate by difficulty/edit scope, and
steps-by-task.

---

## CLI command reference

| Command | Purpose |
|---|---|
| `atelier doctor` | Check models, vector store, and embeddings are healthy |
| `atelier ingest PATH...` | Index notes/PDFs/code into the vector store (`--reset` to rebuild) |
| `atelier ask "Q"` | Grounded answer over your corpus (`-k`, `--show-context`, `--heavy`) |
| `atelier chat` | Interactive knowledge-mode session |
| `atelier sources` | List indexed source files |
| `atelier agent "GOAL"` | Run the autonomous dual-mode agent (`--heavy/--shell/--memory/--max-steps`) |
| `atelier tools` | List the agent's toolbox |
| `atelier remember "FACT"` | Store a durable fact (`--tags`) |
| `atelier recall "Q"` | Semantic search over long-term memory (`-k`) |
| `atelier memory` | List everything in long-term memory |
| `atelier route "TASK"` | Classify a task easy/hard and show the chosen model (`--backend`) |
| `atelier mcp` | Serve the toolbox over MCP (stdio) |
| `atelier eval` | Run the reliability suites (`--mode/--judge/--gate`) |
| `atelier eval-plots` | Generate SVG charts from the latest or selected eval report |

Run `atelier --help` or `atelier <command> --help` for full options.

---

## Configuration reference

Everything is overridable via environment variables (prefix `ATELIER_`) or a
`.env` file in the repo root. Defaults live in [`atelier/config.py`](atelier/config.py).

| Variable | Default | Meaning |
|---|---|---|
| `ATELIER_OLLAMA_URL` | `http://localhost:11434` | Local Ollama endpoint |
| `ATELIER_BRAIN_MODEL` | `qwen3:14b` | Main reasoning / build model |
| `ATELIER_WORKER_MODEL` | `qwen3:4b` | Cheap subtasks, routing target, LLM judge |
| `ATELIER_HEAVY_MODEL` | `gemma4:26b` | Optional heavy reasoner (`--heavy`) |
| `ATELIER_TEMPERATURE` | `0.1` | Sampling temperature |
| `ATELIER_REQUEST_TIMEOUT` | `600` | Per-request timeout (s) |
| `ATELIER_MAX_CONTEXT_CHARS` | `12000` | Cap on retrieved context fed to the model |
| `ATELIER_EMBED_MODEL` | `BAAI/bge-base-en-v1.5` | Local embedding model |
| `ATELIER_EMBED_DEVICE` | `mps` | `mps` (Apple GPU), `cuda`, or `cpu` |
| `ATELIER_CHUNK_SIZE` | `1000` | Chunk size (characters) |
| `ATELIER_CHUNK_OVERLAP` | `150` | Chunk overlap (characters) |
| `ATELIER_RETRIEVAL_K` | `6` | Chunks retrieved per query |
| `ATELIER_USE_HYBRID` | `true` | Fuse dense + BM25 retrieval (RRF) |
| `ATELIER_HYBRID_CANDIDATES` | `20` | Candidates per arm before fusion |
| `ATELIER_RRF_K` | `60` | Reciprocal Rank Fusion constant |
| `ATELIER_RERANK` | `false` | Cross-encoder reranking (downloads ~80 MB once) |
| `ATELIER_RERANK_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Reranker model |

Example:

```bash
export ATELIER_BRAIN_MODEL=gemma4:26b
export ATELIER_RETRIEVAL_K=8
export ATELIER_RERANK=1
```

---

## Models & hardware budget

| Role | Default model | Resident RAM (approx.) | Notes |
|---|---|---|---|
| Brain | `qwen3:14b` (4-bit) | ~9 GB | Comfortable on 36 GB alongside the rest |
| Worker / router target | `qwen3:4b` | ~2.5 GB | Fast iteration, cheap subtasks |
| Heavy (optional) | `gemma4:26b` | ~17 GB | For the hardest reasoning only |
| Embeddings | `bge-base-en-v1.5` | ~0.5 GB | Runs on the Apple GPU (MPS) |
| Router | `Qwen2.5-0.5B` + LoRA | ~1.5 GB (train) | Fine-tune is ~1 min on M3 Pro |

**Rule of thumb:** keep the brain ≤ ~14B so the embedding model, vector store,
tools, and OS all breathe within 36 GB. Don't run the brain and a heavy
fine-tune simultaneously — serialize them.

---

## Reliability results

Latest expanded results with `qwen3:14b` on an M3 Pro, generated with
`atelier eval --mode all` after the repo-map path fix and retrieval-metric
update.

| Metric | Score |
|---|---|
| Knowledge correctness | **94%** (17/18) |
| Knowledge retrieval hit@k | **83%** (15/18) |
| Knowledge citation rate | **100%** (18/18) |
| Code tasks solved | **100%** (13/13) |
| Combined tasks solved | **100%** (10/10) |
| Combined tasks using `search_notes` | **100%** (10/10) |
| Single-line code fixes | **100%** (8/8) |
| Multi-line code fixes | **100%** (5/5) |
| Average code steps | **6.1** |
| Average tool errors | **0.0** |

![Knowledge mode overview](docs/assets/eval/report_20260621T173650/docqa_overview.svg)

![Build mode overview](docs/assets/eval/report_20260621T173650/code_overview.svg)

**Build-mode breakdown**

| Slice | Solved | Finding |
|---|---:|---|
| Easy tasks | **100%** | arithmetic, off-by-one, API misuse, normalization all pass |
| Medium tasks | **100%** | all medium tasks now pass |
| Single-line edits | **100%** | reliable on the expanded suite |
| Multi-line edits | **100%** | the prior weak boundary now passes on this suite |

![Solved by difficulty](docs/assets/eval/report_20260621T173650/code_by_difficulty.svg)

![Solved by edit scope](docs/assets/eval/report_20260621T173650/code_by_edit_scope.svg)

![Steps by task](docs/assets/eval/report_20260621T173650/code_steps_by_task.svg)

The earlier expanded code run failed only `median_bug` and scored 92% (12/13).
Trace inspection showed that the agent was confused by paths from `repo_map`.
After `repo_map` was changed to emit workspace-relative paths, the full code
suite passed: **13/13 solved, 0 tool errors**. `ast_edit` remains available as a
safer compile-checked option for future structural Python edits.

**Combined knowledge → build**

The combined suite tests the actual composition goal: retrieve a project/user
decision from notes, edit code based on that decision, and prove it with tests.
The current 10-task run passed every task and every row used `search_notes`, so
the score is not just accidental code repair.

| Metric | Result |
|---|---:|
| Combined solved | **100%** (10/10) |
| Tests passed | **100%** (10/10) |
| Used `search_notes` | **100%** (10/10) |
| Average steps | **6.7** |
| Average tool errors | **0.0** |

![Combined overview](docs/assets/eval/report_20260622T011056/combined_overview.svg)

![Combined by category](docs/assets/eval/report_20260622T011056/combined_by_category.svg)

The first 10-task combined run briefly scored 9/10 because `router_policy`
triggered a mixed-indentation `ast_edit` input. `ast_edit` now normalizes
common model indentation variants and still compile-checks the whole file before
writing. After that fix, `router_policy` passed in a targeted rerun and the full
combined suite passed at 10/10.

**Knowledge-mode breakdown**

![Correctness by doc-QA category](docs/assets/eval/report_20260621T173650/docqa_by_category.svg)

The knowledge suite is mostly correct, and citation discipline is now perfect on
this run. Retrieval hit@k improved from 61% to 83% after allowing multiple valid
expected sources where the same fact appears in several project docs.

**Suite size**

| Suite | Size | What it probes |
|---|---:|---|
| Doc-QA | 18 tasks | constraints, architecture, RAG, tools, models, usage, evaluation |
| Code repair | 13 tasks | arithmetic, off-by-one, normalization, mutation, order preservation, structural logic |
| Combined | 10 tasks | retrieve a project/user decision, then make a verified code change |

Earlier baseline on the smaller 8+3 suite was 100% doc-QA correctness and 67%
code solved. The expanded run is more informative: it shows build mode is now
reliable on this 13-task single-file repair suite after the path-handoff fix.

**Router (fine-tuned 0.5B)**

| Metric | Value |
|---|---|
| Base accuracy (held-out) | 43.8% |
| Fine-tuned accuracy | **100%** (+56 pts) |
| Brain calls saved (doc-QA) | **50%**, with **0 accuracy loss** |

---

## Reproduce everything

```bash
make reproduce        # env → models → tests → eval → train + evaluate router
make help             # list all tasks
```

Or step by step:

```bash
make setup            # uv venv + install
make test             # unit suite (no model)
make ingest           # index the sample corpus
make eval             # reliability eval
make eval-plots       # SVG charts for the latest eval report
make planner-data     # build task -> plan/router SFT data from eval metadata
make train-planner-router # fine-tune planner-router adapter from planner_data
make train-router     # LoRA fine-tune + evaluate the router (~1 min)
make route-eval       # measure routing savings
make demo             # quick end-to-end build-mode demo
```

Artifacts produced: the trained adapter (`models/router/adapter/`), JSON reports
(`data/eval_reports/`), and per-run traces (`data/traces/`).

---

## Testing

A complete, ability-by-ability test playbook (with expected outputs) lives in
[`docs/TESTING.md`](docs/TESTING.md). The fast automated suite needs **no model**:

```bash
pytest -q             # fast tests: tools, sandbox/escape guards, chunking,
                      # vector store, ReAct engine, memory, retrieval, router, eval
```

The tests that touch the live model (knowledge/build/eval) are run on demand via
the `atelier` commands and `make` targets, not in the fast suite.

---

## Project structure

```
atelier/
├── README.md                 # this file
├── PROJECT.md                # source of truth: scope, constraints, roadmap, decisions
├── Makefile                  # `make help` — common tasks
├── pyproject.toml            # installable package + the `atelier` command
├── requirements.txt          # pinned, reproducible dependencies
│
├── atelier/                  # cross-cutting: config, CLI, MCP server, banner
│   ├── config.py             #   all settings (env-overridable)
│   ├── cli.py                #   the `atelier` command (typer)
│   ├── mcp_server.py         #   publishes the toolbox over MCP
│   └── banner.py             #   the magician banner
│
├── agent/                    # the agent itself
│   ├── react.py              #   registry-driven ReAct engine (reflection, traces)
│   ├── brain.py              #   Ollama client (model roles, JSON mode, streaming)
│   ├── memory.py             #   persistent semantic long-term memory
│   ├── router.py             #   fine-tuned + heuristic difficulty router
│   └── loop.py               #   the original Phase-0 loop (kept for reference)
│
├── tools/                    # the shared toolbox (one registry, two modes)
│   ├── registry.py           #   register/validate/dispatch tools
│   ├── files.py              #   read/write/edit (workspace-sandboxed, syntax-checked)
│   ├── ast_edit.py           #   AST-aware Python function body replacement
│   ├── code_exec.py          #   sandboxed Python execution
│   ├── test_runner.py        #   pytest runner — build mode's verifier
│   ├── repo_map.py           #   AST outline of a codebase
│   ├── search.py             #   local grep-like search
│   ├── knowledge.py          #   search_notes (RAG as a tool)
│   ├── memory_tools.py       #   remember / recall
│   ├── calculator.py         #   AST-sandboxed arithmetic
│   └── shell.py              #   opt-in shell tool
│
├── rag/                      # knowledge mode
│   ├── ingest.py · chunk.py  #   load + heading-aware chunking
│   ├── embed.py · store.py   #   local embeddings + ChromaDB
│   ├── lexical.py            #   BM25 (the keyword arm of hybrid)
│   ├── retrieve.py           #   dense + BM25 fused via RRF (+ optional rerank)
│   ├── rerank.py             #   optional cross-encoder reranker
│   └── answer.py             #   grounded, cited answers
│
├── eval/                     # reliability harness
│   ├── tasks_docqa/          #   frozen knowledge-mode suite
│   ├── tasks_code/           #   frozen build-mode suite (repo + bug + hidden test)
│   ├── tasks_combined/       #   knowledge -> build suite
│   ├── metrics.py            #   scoring + local LLM-as-judge
│   ├── run_eval.py           #   runner, reports, regression gate
│   └── route_eval.py         #   routing-savings measurement
│
├── models/router/            # Phase 6 fine-tune
│   ├── make_dataset.py       #   synthetic difficulty dataset
│   ├── make_planner_dataset.py # eval metadata -> planner/router SFT data
│   ├── evaluate.py           #   base vs fine-tuned accuracy
│   └── adapter/              #   the trained LoRA adapter (~6 MB)
│
├── scripts/reproduce.sh      # one-command reproduction
├── tests/                    # fast unit tests (no model)
└── docs/
    ├── ARCHITECTURE.md       # how the pieces fit
    ├── TESTING.md            # ability-by-ability test playbook
    ├── EVAL.md               # reliability results + honest caveats
    └── WRITEUP.md            # the public writeup + figure
```

Runtime data (the vector store, traces, eval reports, memory) lives under `data/`
and is gitignored — it's local and regenerable.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `atelier doctor` shows a model **red** | Run the `ollama pull <model>` it prints; ensure `ollama serve` is running |
| "Could not reach Ollama" | Start Ollama (`ollama serve`) or set `ATELIER_OLLAMA_URL` |
| `atelier` command not found | `uv pip install -e .` (or use `python -m atelier.cli ...`) |
| First `ask`/`ingest` is slow | One-time embedding-model download; subsequent runs are fast |
| Embeddings fall back to CPU | Expected if MPS is unavailable; set `ATELIER_EMBED_DEVICE=cpu` to silence |
| Agent loops without finishing | Lower task complexity, raise `--max-steps`, or try `--heavy` |
| Banner clutters piped output | `export ATELIER_NO_BANNER=1` |
| Knowledge base "empty" | Run `atelier ingest <path>` first; check `atelier sources` |

---

## Limitations (read these)

This project values honest limits over optimism:

- **It will not beat cloud coding agents** (Claude Code, Cursor). A local small
  model can't, and that's an explicit non-goal.
- **Multi-line structural code edits are still the risk boundary** for the 14B
  brain. The current suite passes, but the project handles this by using
  compile-checked tools like `ast_edit`, not by assuming the model is perfect.
- **The eval suites are still modest** (18 doc-QA + 13 code + 10 combined).
  100% on a slice means "no failures on this frozen suite," not "robust at
  scale."
- **The router's held-out test is in-distribution** (templated). It generalizes
  well in spot-checks but isn't a generalization benchmark.
- **Correctness scoring is keyword-based** by default; the optional local
  LLM-judge is a second, also-fallible opinion.

---

## Further reading

- [`PROJECT.md`](PROJECT.md) — the source of truth: scope, hard constraints, the
  full roadmap, the Decision Log, and the Changelog.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how every layer fits together.
- [`docs/TESTING.md`](docs/TESTING.md) — verify each capability yourself.
- [`docs/EVAL.md`](docs/EVAL.md) — reliability numbers and caveats.
- [`docs/WRITEUP.md`](docs/WRITEUP.md) — the public writeup with the figure.

---

## License

[Apache-2.0](LICENSE).

<div align="center"><sub>Built to run entirely on one laptop, at $0. Your notes and code never leave the machine.</sub></div>
