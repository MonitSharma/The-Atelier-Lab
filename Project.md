# PROJECT.md — Atelier

> A from-scratch, fundamentals-to-expert project to build a reliable, openly-evaluated
> agent that runs entirely on a single MacBook, at zero cost. The agent is the system.
> It has two capability modes that share one harness:
>   (1) **Knowledge mode** — research and synthesis over my own documents (RAG).
>   (2) **Build mode** — developer tooling: read a repo, edit code, run tests, fix failures.
> A locally fine-tuned small reasoning model plugs in later as a cheap component.

**Name:** Atelier
**Status:** Knowledge mode + build mode both usable. Phase 1/2/4-core shipped; next: MCP exposure, memory (Phase 3), eval harness (Phase 5)
**Owner:** Monit
**Last updated:** 2026-06-21
**One-line research question / repo description:** *"How far can a fully local, zero-cost agent go at understanding my knowledge and working on my code — on a single laptop?"*
**Repo role of this file:** Single source of truth for scope, constraints, roadmap, and decisions. Read it before doing anything.

---

## 0. How to use this file

**For me (the human):** This is the doc I look back at to remember why I made a decision, what the current phase is, and what "done" means. I update the Decision Log and Changelog whenever something changes. I do not let the plan drift silently.

**For an AI assistant (e.g. Claude Code) reading this file:** Treat the rules below as binding.

1. **Read `## 1. Hard constraints` first, every time.** They are non-negotiable. Never propose anything that violates them.
2. **Never suggest paid, cloud, or subscription services** (no OpenAI/Anthropic/Google APIs, no rented GPUs, no paid vector DBs, no SaaS). Everything must run locally on the Mac for free. If a task seems to *need* a paid service, say so explicitly and propose the best free local alternative instead — do not quietly assume an API.
3. **Check `## 8. Roadmap` for the active phase.** Help advance the *current* phase. Do not jump ahead to later phases unless asked.
4. **Prefer build-from-scratch over frameworks** until the relevant primitive is understood (see the sequencing rule in §8). When a framework is appropriate, prefer free/open-source/local-compatible ones.
5. **When we make a decision, append it to `## 12. Decision log`. When the project state changes, append to `## 16. Changelog`.** Keep both terse.
6. **Be honest about limits.** This project values realistic guidance and hard limits over optimism. If something won't work on this hardware, say so plainly.
7. **Tooling moves fast.** Versions and "best" libraries in §6/§10 may be stale — verify current state before relying on a specific version, but keep the categories.

---

## 1. Hard constraints (non-negotiable)

| Constraint | Detail |
|---|---|
| **Hardware** | MacBook M3 Pro, 36 GB unified memory, macOS. This is the *only* machine. |
| **Cost** | $0. No purchases, no subscriptions, no cloud APIs, no rented compute. Ever. |
| **Locality** | Everything runs locally. Model inference, embeddings, vector store, tools, orchestration — all on-device. |
| **No new hardware** | No eGPU, no second machine, no cloud burst. Design within 36 GB. |
| **Privacy** | A side benefit of local-only: my documents and code never leave the machine. Lean into this as a feature — it's a real selling point for a knowledge agent. |

These constraints are the *point*, not a limitation to work around. "How far can a fully local, zero-cost agent go on one laptop?" is itself the research question.

---

## 2. The big picture

**The agent is the system.** It is one harness — loop, tools, memory, retrieval, evaluation — that powers two capability modes:

- **Knowledge mode (research over my documents).** Ingest my papers, notes, PDFs, and docs; retrieve and synthesize answers grounded in them. This is the "second brain" half. *Verifier:* a graded Q&A eval set + retrieval-quality metrics.
- **Build mode (developer tooling).** Read a repository, navigate code, edit it, run the test suite, and fix failing tests — proving the fix with a green run. This is the "engineering" half. *Verifier:* the test suite itself (clean pass/fail).

The two modes compose into the end goal: an agent that can use my knowledge base *and* act on my codebase in one task — e.g. "using my notes on X, implement Y in this repo and prove it with tests."

- **The fine-tuned small reasoning model is a component** (Phase 6) — a cheap local worker / router for easy subtasks, so the main brain is reserved for hard steps. (This is where any earlier SFT/LoRA work plugs in.)
- The expertise being built is **applied agent + LLM systems engineering**. The hard, valuable part is the harness — context engineering, memory, orchestration, and above all **evaluation and reliability** — not the agent loop, which is simple.
- **Why this domain:** coding agents and "talk to my documents" are the two highest-demand applications of the current AI boom. Both are buildable on a laptop, both are verifiable, and a rigorous local-first reliability study of them is genuinely attention-worthy.

---

## 3. Scope and non-goals (read this when ambition creeps)

**In scope / achievable on this setup:**
- A working, local, zero-cost agent that measurably helps real work: answering questions over my own corpus, and making verified code changes in a repo.
- Genuine expertise in agent architecture, RAG, evaluation, and local LLM ops.
- Open, reproducible artifacts and an honest reliability writeup (workshop-paper / strong-blog-post tier).

**Explicit non-goals (do not chase these):**
- Beating frontier cloud coding agents (Claude Code, Cursor, etc.). Will not happen with a local small model; not the goal.
- "Magic" / fully autonomous general agent. Aim for *reliable and narrow*, not magical and broad.
- Frontier pretraining research. Different track, needs clusters. Out of scope.
- 24/7 production / always-on autonomy. This is an on-demand assistant, not a service.

**The binding limit** is not the 36 GB of RAM. It is (a) the reasoning ceiling of a model small enough to run locally, and (b) error compounding across multi-step agent runs. Design around these.

---

## 4. Architecture overview (local-first)

```
                 +-------------------------------------------+
                 |              Orchestrator / loop          |
                 |   (perceive -> plan -> act -> observe)     |
                 +----+--------------+-----------------+------+
                      |              |                 |
              +-------v---+   +------v------+   +-------v--------+
              |  Brain    |   |   Tools     |   |   Memory       |
              | local LLM |   | (via MCP)   |   | short + long   |
              | 8-14B     |   |             |   |                |
              +-----------+   | - code exec |   | - scratchpad   |
                    |         | - file r/w  |   | - long-term    |
            +-------v------+  | - test_run  |   +-------+--------+
            | Router /     |  | - repo map  |           |
            | cheap worker |  | - search    |   +-------v--------+
            | (fine-tuned  |  | - shell     |   |  Knowledge /   |
            |  small model)|  +-------------+   |  RAG store     |
            +--------------+                    | (my documents) |
                                                +----------------+

Two modes share this harness:
  KNOWLEDGE mode  -> leans on RAG store + synthesis; verified by graded Q&A.
  BUILD mode      -> leans on repo map + code exec + test_run; verified by tests.
```

- **Brain:** a local, code-capable 8–14B model (e.g. Qwen3-8B) served via Ollama / LM Studio / MLX.
- **Router / cheap worker:** the locally fine-tuned small model (Phase 6); triages easy subtasks.
- **Tools (via MCP):** file r/w, sandboxed code execution, **test runner** (run suite, parse pass/fail), repo map / code navigation, search (local + web), shell. The test runner is the *verification mechanism* for build mode — same role the simulator played in the earlier quantum draft.
- **Knowledge / RAG store:** local embeddings + local vector store over my documents.
- **Memory:** working scratchpad + persistent long-term store.
- **Eval harness:** cross-cutting and the most important part (see §9). Holds two frozen task suites: doc-QA and coding.

---

## 5. Proposed repository structure

```
atelier/
├── PROJECT.md                # this file — source of truth
├── README.md                 # short public-facing summary
├── LICENSE                   # MIT or Apache-2.0 (free, open)
├── pyproject.toml            # deps via uv
├── agent/
│   ├── loop.py               # the core ReAct loop (Phase 0, hand-written)
│   ├── brain.py              # local model client (Ollama/MLX)
│   ├── router.py             # cheap-worker routing (Phase 6)
│   ├── memory/               # scratchpad + long-term memory (Phase 3)
│   └── orchestrator.py       # planning / sub-agents (Phase 4)
├── tools/                    # MCP tool servers (Phase 1+)
│   ├── code_exec.py          # sandboxed execution
│   ├── files.py              # read/write/edit files
│   ├── test_runner.py        # run test suite, parse pass/fail (build-mode verifier)
│   ├── repo_map.py           # navigate/structure a codebase
│   └── search.py             # local + web search
├── rag/                      # knowledge mode (Phase 2)
│   ├── ingest.py             # load my docs/notes/PDFs/code
│   ├── embed.py              # local embedding model
│   ├── retrieve.py           # retrieval into the loop
│   └── store/                # local vector store
├── eval/                     # the eval harness (Phase 5) — most important dir
│   ├── tasks_docqa/          # frozen knowledge-mode task suite
│   ├── tasks_code/           # frozen build-mode task suite (repo + bug + hidden test)
│   ├── run_eval.py
│   ├── metrics.py
│   └── traces/               # logged runs for debugging/regression
├── models/                   # fine-tuned adapters, configs (Phase 6)
├── notebooks/                # exploration
└── docs/
    └── writeup/              # the eventual blog post / paper
```

---

## 6. Tech stack (all local, all free)

- **Env/deps:** `uv` (fast, reproducible).
- **Local serving:** Ollama (simplest for the agent loop — Python client + HTTP endpoint) and/or LM Studio (GUI + OpenAI-compatible local server); MLX / `mlx-lm` for Apple-Silicon-native inference and any fine-tuning; llama.cpp under the hood for GGUF.
- **Brain model:** a code-capable Qwen3-8B (4-bit) as default; a 3B (e.g. SmolLM3-3B) for fast iteration / cheap worker.
- **Embeddings:** a small local embedding model (run via MLX or Ollama). No paid embedding APIs.
- **Vector store:** a local, free, embeddable store (e.g. a file-/SQLite-backed vector index). No hosted DB.
- **Tool protocol:** MCP.
- **Orchestration (Phase 4+, after hand-rolling first):** prefer free/open-source, local-compatible, debuggable frameworks. Verify current options before committing.
- **Sandboxing:** code execution must be sandboxed even locally (subprocess limits / temp dirs / no network by default).

> Versions and "best framework" change fast — confirm current state at the time you reach each phase. Categories above are stable; specifics are not.

---

## 7. Hardware / memory budget cheatsheet (36 GB)

| Workload | Fits? | Notes |
|---|---|---|
| 8B brain @ 4-bit, inference | Comfortable | ~5–6 GB; leaves room for tools + OS |
| 14B brain @ 4-bit, inference | Fits | tighter; fine if not also training |
| 32B @ 4-bit, inference | Tight | possible but leaves little headroom for agent stack |
| Local embedding model | Trivial | runs alongside the brain |
| Vector store + tools + orchestration | Light | negligible RAM |
| Fine-tuning small model (QLoRA, 3–8B) | Comfortable | do this when iterating on the component model, not while the agent is serving |
| Running brain + heavy training simultaneously | Don't | serialize these |
| 70B anything | No | inference and training both impractical |

**Rule:** the agent's RAM budget = brain + embeddings + working set. Keep the brain ≤ ~14B so the rest of the stack breathes.

---

## 8. Roadmap (fundamentals → expert)

**Sequencing rule:** build each capability *by hand first* to learn the fundamental, then adopt a framework only once you understand the primitive it hides. Each phase ships a capability and teaches a concept. Estimated total: ~4–6 months part-time.

Mark progress with `[ ]` / `[x]`.

### Phase 0 — The loop, from scratch
- **Goal:** a bare ReAct loop, no framework, one tool, local model.
- **Learn:** what an agent fundamentally is; model-as-reasoner + tools + loop; structured-output parsing.
- **Build:** `agent/loop.py`, `agent/brain.py`; serve Qwen3-8B locally; one tool (a calculator or file-read — pick one with verifiable output).
- **Definition of done:** the loop takes a goal, calls the one tool, reads the result, and produces a final answer — observed working on 5 hand-written tasks.
- **Checklist:**
  - [x] Local model serving verified (Ollama / `mlx_lm.generate` responds)
  - [x] Hand-written perceive→plan→act→observe loop runs
  - [x] One tool wired with structured-output parsing
  - [x] 5 manual smoke tests pass

### Phase 1 — Tools and the protocol (MCP)
- **Goal:** real tools behind a standard protocol — the shared toolbox both modes use.
- **Learn:** tool schemas, function calling, common failure modes (hallucinated args, malformed calls).
- **Build:** `tools/` — file r/w, sandboxed code execution, search, shell; expose via MCP.
- **Definition of done:** agent can choose among ≥4 tools and recover from at least one tool-error type.
- **Checklist:**
  - [ ] MCP tool server scaffold (tools exist; not yet exposed over MCP)
  - [x] files, code_exec, search, shell tools (+ write/edit, repo_map, test_runner, search_notes)
  - [x] Sandbox for code execution (subprocess + timeout + macOS seatbelt network deny)
  - [x] Error handling for malformed tool calls (reflection in `agent/react.py`)
  - [x] Logged examples of correct tool selection (every run traced to `data/traces`)

### Phase 2 — Knowledge mode: context engineering + RAG over my documents
- **Goal:** the agent starts actually helping — answering questions grounded in my own corpus.
- **Learn:** chunking, retrieval, context-window budgeting; that context engineering is most of the real work.
- **Build:** `rag/` — ingest my papers/notes/PDFs/code; local embeddings; local vector store; wire retrieval into the loop.
- **Definition of done:** agent answers ≥5 questions about my own corpus that it cannot answer without retrieval; a before/after comparison shows the lift.
- **Checklist:**
  - [x] Corpus ingested and chunked (`rag/ingest.py`, `rag/chunk.py`; md/txt/pdf/code)
  - [x] Local embedding pipeline (`rag/embed.py`, bge-base on MPS) + ChromaDB store (`rag/store.py`)
  - [x] Retrieval → grounded answer path (`rag/retrieve.py`, `rag/answer.py`, `atelier ask`)
  - [ ] Retrieval wired into the *agent loop* as a tool (currently a direct answer path)
  - [ ] Before/after comparison on corpus-specific questions (Phase 5 eval)

### Phase 3 — Memory and state
- **Goal:** the agent remembers within and across sessions.
- **Learn:** statefulness; why naive "stuff everything in context" memory breaks.
- **Build:** `agent/memory/` — working scratchpad + persistent long-term memory.
- **Definition of done:** agent recalls a fact from a prior session and uses it correctly.
- **Checklist:**
  - [ ] Scratchpad working memory
  - [ ] Persistent long-term store
  - [ ] Session persistence verified

### Phase 4 — Build mode + planning, decomposition, reflection
- **Goal:** reliable multi-step behavior, and the first real coding capability.
- **Learn:** the crux — where reliability breaks down as errors compound; why multi-step agents fail.
- **Build:** `tools/repo_map.py` and `tools/test_runner.py`; task decomposition; a self-critique/reflection loop; a simple orchestrator + workers (`agent/orchestrator.py`). The reflection loop is what lets build mode read a test failure and try again. Adopt a framework here only if it earns its place.
- **Definition of done:** agent fixes a failing test in a small sample repo across a 3+ step run, using a reflection step that catches at least one of its own errors, and proves the fix with a green test run.
- **Checklist:**
  - [x] repo_map + test_runner tools
  - [x] Decomposition of a multi-step coding task (verified: map→read→edit→test→done)
  - [x] Reflection / self-critique loop (read failure → retry; tested in `test_react.py`)
  - [ ] Orchestrator + worker pattern (single agent for now; multi-agent later)
  - [ ] Documented failure analysis of a hard multi-step run (needs eval harness, Phase 5)

### Phase 5 — Evaluation and reliability (the real frontier discipline)
- **Goal:** the thing that separates a demo from a system; the core of the eventual writeup.
- **Learn:** agent evaluation, trace observability, regression testing — for both modes.
- **Build:** `eval/` — two frozen task suites (`tasks_docqa/`, `tasks_code/`), success metrics, full trace logging, regression tests.
- **Definition of done:** one command runs both suites and reports success rate + per-task traces; a regression that helps one task and breaks others is caught automatically.
- **Checklist:**
  - [x] Frozen, version-controlled doc-QA suite (`eval/tasks_docqa/tasks.json`, 6 graded Qs)
  - [x] Frozen, version-controlled coding suite (`eval/tasks_code/`: add_bug, offbyone — repo + bug + hidden test)
  - [x] Success metrics + scoring for each mode (`eval/metrics.py`: keyword, retrieval hit, citation, + optional local LLM-as-judge)
  - [x] Trace logging for every run (`agent/react.py` → `data/traces/`)
  - [x] Eval runner with saved reports (`eval/run_eval.py`, `atelier eval`; reports → `data/eval_reports/`)
  - [ ] Automated regression gate comparing report-to-report (reports are saved; diffing CLI still TODO)

### Phase 6 — Specialization and composition
- **Goal:** fold in the cheap component model; make the two modes work together.
- **Learn:** cost/latency/quality routing; the model-as-component mindset.
- **Build:** plug in the fine-tuned small model as router/cheap worker (`agent/router.py`); routing policy (easy → cheap worker, hard → brain); a combined task that uses knowledge mode to inform build mode (retrieve from my docs, then make a verified code change).
- **Definition of done:** routing measurably reduces brain calls on easy subtasks without hurting success rate; agent completes ≥3 combined knowledge→build tasks with test-verified outputs.
- **Checklist:**
  - [ ] Fine-tuned model integrated as worker/router
  - [ ] Routing policy with measured savings
  - [ ] Combined knowledge→build task working
  - [ ] Combined tasks added to `eval/`

### Phase 7 — Capstone and release
- **Goal:** a useful, evaluated, open agent + a writeup.
- **Learn:** packaging, reproducibility, scientific communication.
- **Build:** one-command reproduction, README, `docs/writeup/`.
- **Definition of done:** a stranger can clone, run the eval, and reproduce my reliability numbers; writeup published.
- **Checklist:**
  - [ ] One-command setup + repro
  - [ ] Public README + reliability figure
  - [ ] Honest failure analysis written up
  - [ ] Artifacts released (repo + adapters + eval harness)

---

## 9. Evaluation & reliability discipline (cross-cutting)

This is the spine of the whole project and the part that makes it credible.

- **Freeze the task suites** early and version-control them. Never edit casually; changing the ruler invalidates comparisons.
- **Metrics to track:**
  - *Both modes:* task success rate; steps-to-success; tool-error rate; self-correction rate; latency/tokens.
  - *Build mode:* test pass rate (the clean, objective signal); regressions introduced.
  - *Knowledge mode:* answer correctness on graded Q&A; retrieval hit rate / relevance; groundedness (does the answer cite retrieved context, or hallucinate?).
- **Log every run** as a trace so failures are debuggable after the fact.
- **Regression test** on every meaningful change.
- **Report honestly**, including where it fails. Negative results and error bars are features, not embarrassments. This is the difference between a demo and research.

---

## 10. Attention-worthy / publishing angle

Reach comes from rigor and openness, not flashy demos. The differentiator:

- A **published, reproducible reliability evaluation** of a local-first dual-mode agent: "here's how often a laptop-sized agent answers my-corpus questions correctly and how often it makes a test-passing code fix, where it fails, and how the local-vs-bigger-model gap looks."
- **One clear figure** (e.g. success rate vs task difficulty, or routing savings vs success, for each mode).
- **Open artifacts** + one-command repro.
- **Honest failure analysis.**
- Target venue: an ML-efficiency / on-device / open-source / agents workshop, or a strong technical blog post. Realistic and within reach; main-conference tracks are not the goal.

---

## 11. Risks & open questions (revisit each phase)

- **Local brain reasoning ceiling** — at what task difficulty does the 8–14B brain stop being reliable, for each mode? (Measure it; this is research.)
- **Error compounding** — how many steps before reliability collapses? Mitigation: reflection, the test-runner as a verifier, decomposition.
- **Retrieval quality** — bad retrieval silently produces confident wrong answers; measure groundedness, not just answer text.
- **Context limits** — corpus may outgrow the context window; rely on retrieval, not stuffing.
- **Tool sandbox safety** — code execution must be sandboxed even locally.
- **Scope creep** — re-read §3 whenever a new shiny capability tempts a detour.
- **Open question:** does the fine-tuned router actually save enough to justify its complexity? (Phase 6 must measure, not assume.)

---

## 12. Decision log (append-only)

> Format: `YYYY-MM-DD — decision — rationale`

- 2026-06-13 — Commit to fully local, zero-cost, single-Mac design — core constraint and the project's research premise.
- 2026-06-13 — Agent is the umbrella; fine-tuned model is a component — unify prior threads into one body of work.
- 2026-06-13 — Build-from-scratch before frameworks — to learn fundamentals, not just wire primitives.
- 2026-06-13 — Drop the quantum domain — it was a forced fit; the agent/harness work was never quantum-dependent.
- 2026-06-13 — Two domains, one harness: knowledge mode (RAG over my documents) + build mode (coding/dev tooling) — both high-demand, both buildable locally, both verifiable (Q&A grading + test runner).
- 2026-06-13 — Name the project "Atelier" — names what it is (a personal space holding knowledge and tools), keeps freedom to retarget the domain later.
- 2026-06-21 — Supersede the strict "build-from-scratch, one phase at a time" methodology (§8 sequencing rule) for the product track — owner chose to build the full dual-mode product now, knowledge mode first. The learning intent stays in the doc as history; framework use (ChromaDB, sentence-transformers, typer) is now allowed where it earns its place, still local + zero-cost.
- 2026-06-21 — Embedding model = `BAAI/bge-base-en-v1.5` (768-dim, MPS), with the bge query instruction prepended to queries only — strong retrieval quality at trivial cost on M3 Pro; fully local. Overridable via `ATELIER_EMBED_MODEL`.
- 2026-06-21 — Model roles fixed: brain=`qwen3:14b`, worker=`qwen3:4b`, heavy=`gemma4:26b` (the three pulled locally) — replaces the placeholder "Qwen3-8B" in earlier drafts.
- 2026-06-21 — Vector store = ChromaDB (local PersistentClient, cosine), embeddings supplied by us (no Chroma embedding fn) so the store needs no network and stays in lockstep with `rag.embed`.

---

## 13. Glossary (fundamentals → expert)

Terms to understand deeply as you progress (look each up when you reach it):

- **Agent loop / ReAct** — perceive → reason → act → observe cycle.
- **Tool / function calling** — model emits a structured call; runtime executes it.
- **MCP (Model Context Protocol)** — standard interface for exposing tools to models.
- **RAG** — retrieval-augmented generation; inject retrieved context at inference.
- **Embedding / vector store** — text → vectors; nearest-neighbour retrieval.
- **Chunking** — splitting documents for indexing/retrieval.
- **Groundedness** — whether an answer is supported by retrieved context vs hallucinated.
- **Context engineering** — deciding what goes in the context window and how.
- **Repo map** — a structured view of a codebase the agent navigates.
- **Test-driven verification** — using a test suite as the objective signal for a code change.
- **Working vs long-term memory** — scratchpad vs persistent store.
- **Decomposition / planning** — breaking a goal into sub-steps.
- **Reflection / self-critique** — agent reviews and corrects its own output (e.g. reads a test failure and retries).
- **Orchestration / sub-agents** — coordinating multiple roles or steps.
- **Routing** — sending each subtask to the cheapest model that can do it.
- **Eval harness / trace / regression test** — how reliability is measured and protected.
- **LoRA / QLoRA / SFT / DPO / GRPO** — fine-tuning techniques for the component model.
- **Quantization (4-bit)** — shrinking a model to fit memory.

---

## 14. Resources to look up (categories, not stale links)

- Official docs for: MLX / `mlx-lm`, Ollama, LM Studio, MCP.
- Agent-pattern writeups: ReAct, reflection, planner-executor, multi-agent orchestration.
- Coding-agent evaluation: SWE-bench-style task formats (repo + issue + hidden test) for inspiration on building your own small suite.
- RAG evaluation: retrieval metrics and groundedness/faithfulness scoring.
- Local RAG and local embedding guides for Apple Silicon.
- The DeepSeek-R1 / GRPO lineage for reasoning fine-tuning (component model, Phase 6).

> Verify currency before relying on any specific version or "best" claim.

---

## 15. Definition of "expert" for this project

By the end you should be able to: design and hand-build an agent loop; reason about and mitigate multi-step failure; engineer context and memory; build a RAG pipeline and evaluate retrieval honestly; use test-driven verification to make an agent's code changes trustworthy; build and defend an evaluation harness; run local models and fine-tune a small one; and compose a fine-tuned component into a larger system via routing. That is genuine applied-agent/LLM-systems expertise — the realistic and valuable target. Not: frontier pretraining, not magic, not beating cloud labs.

---

## 16. Changelog (append-only)

- 2026-06-13 — Project file created. Status: Planning → Phase 0.
- 2026-06-13 — Retargeted from quantum domain to a dual-mode agent (knowledge mode over my documents + build mode for coding/dev tooling). Renamed to Atelier. Verifier changed from quantum simulator to test runner + retrieval grader. Eval split into two frozen suites.
- 2026-06-16 — Phase 0 completed. Standalone perceive-plan-act-observe agent loop with local Ollama qwen3 integration and secure AST calculator verified with smoke tests. Status updated to Phase 1.
- 2026-06-21 — Productized the stack: added `pyproject.toml` (installable `atelier` CLI), central `atelier/config.py` (pydantic-settings), `.gitignore`, `README.md`. Upgraded `agent/brain.py` to the ollama client with model roles (brain/worker/heavy), JSON mode, streaming, and qwen3 think-trace stripping. Fixed `tools/registry.py` `prompt_description` bug (early `return` inside the loop hid every tool but the first).
- 2026-06-21 — Knowledge mode (Phase 2) shipped end-to-end: `rag/` = ingest (md/txt/pdf/code) → heading-aware chunking → local bge embeddings → ChromaDB → retrieval → grounded, cited answers. CLI: `atelier ingest|ask|chat|sources|doctor`. Verified on the real corpus (Project.md, myNotes.md): 64 chunks, 768-dim, correct cited answer to a notes-only question. Added `tests/test_chunk.py`, `tests/test_store.py`.
- 2026-06-21 — Evaluation harness (Phase 5 core) shipped — the reliability spine. `eval/` = two frozen suites (doc-QA over the real corpus; code tasks = repo+bug+hidden test), deterministic metrics (keyword coverage, retrieval hit@k, citation rate) + optional local LLM-as-judge (worker model grades correctness/groundedness, no cloud). `eval/run_eval.py` runs both modes in isolated `.eval_workspace/` copies, verifies code tasks with the real pytest runner, and writes JSON reports to `data/eval_reports/`. CLI `atelier eval [--mode docqa|code|all] [--judge]`. Harness logic unit-tested in `tests/test_eval.py` (metrics + code-runner with a fake agent). Live numbers recorded in `docs/EVAL.md`.
- 2026-06-21 — Build mode (Phase 1 + Phase 4 core) shipped: full toolbox — `write_file`/`edit_file` (workspace-sandboxed), `code_exec` (subprocess + timeout + macOS seatbelt network block), `test_runner` (pytest, parsed), `repo_map` (ast outline), local `search`, `search_notes` (RAG-as-a-tool), opt-in `shell`. Registry-driven ReAct engine (`agent/react.py`) with reflection on errors, observation capping, and trace logging to `data/traces`. CLI `atelier agent|tools`. **Verified live**: agent autonomously fixed a failing test in `sample_task/` in 6 steps (repo_map→read→read→edit→test_runner→final), proven by an independent green run. Added a magician ASCII banner. Added `tests/test_tools_build.py`, `tests/test_react.py`, `tests/test_calculator.py`; full suite 35 green. Wrote `docs/TESTING.md` (ability-by-ability test playbook).