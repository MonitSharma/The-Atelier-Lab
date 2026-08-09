# Atelier Workbench plan

## Destination

The Atelier Lab is becoming a local-first AI workbench for the Mac: a general-purpose AI layer over files, documents, code, research, and deterministic tools.

The user should interact with the workbench rather than with individual models. The workbench should be accessible through a web UI, an `atelier` terminal command, and eventually Finder actions such as “Send to Atelier”.

It is not a coding-only agent, a PDF chatbot, an Ollama wrapper, or a collection of unrelated model interfaces.

## End-state architecture

```text
YOU
 │
 ├── Web UI
 ├── atelier CLI
 └── Finder actions
       │
       ▼
ATELIER WORKBENCH
       │
       ▼
TASK ROUTER
       │
 ┌─────┼──────────┬──────────┬─────────┐
 ▼     ▼          ▼          ▼         ▼
Docs  Code     Research     Data    General
 │     │          │          │         │
 └─────┴──────────┴──────────┴─────────┘
       │
       ▼
TOOL / AGENT HARNESS
       │
       ▼
MODEL ROUTER
       │
 ┌─────┼──────────┬──────────┬─────────┐
 ▼     ▼          ▼          ▼         ▼
Tiny  Coder   Multimodal  Large   Embedding
local local      local     local    model
       │
       ▼
Verification → optional escalation to Claude, Codex, or Gemini
```

The local system must remain useful when the internet is unavailable. Cloud models are optional escalation paths, not core dependencies.

## What the workbench should feel like

### Papers and documents

Dropping a paper into Atelier should eventually trigger a staged workflow:

1. identify title, authors, year, and metadata;
2. extract text and determine whether OCR is necessary;
3. characterize the field, problem, method, contribution, theory/experiment status, code, hardware, and research relevance;
4. produce a short local characterization;
5. index the source locally;
6. offer deeper actions such as explain, deep read, find weaknesses, compare, reproduce, extract equations, inspect code, and find related work.

Native PDF parsing comes first. OCR is invoked only when the parser finds insufficient usable text.

### Code and repositories

Repository understanding should be staged rather than sending every file to a large model:

```text
folder → file tree → language/environment detection → important files
       → symbols/imports → small coding model → deterministic tools
       → large local reasoning → optional frontier escalation
```

Deterministic tools should inspect files, search symbols, run tests, inspect Git, and measure results before an LLM is asked to explain or modify the project.

### General files

The workbench should eventually characterize CSV, JSON, Parquet, SQLite, spreadsheets, images, LaTeX, notebooks, presentations, and unstructured text. The product is therefore a workbench, not a chatbot.

## System layers

### 1. Local model runtime — Ollama

Ollama is the local inference engine. It should expose models, structured JSON outputs, tool/function calling, and embeddings to the rest of Atelier.

Ollama is the engine room, not the intelligence orchestrator.

### 2. Apple model laboratory — MLX / MLX-LM

MLX-LM remains separate from daily Ollama inference. It is for Apple-Silicon experiments, benchmarking, quantization, LoRA, fine-tuning, and router experiments. It is not required for version 1.

### 3. Replaceable user interface — Open WebUI initially

Open WebUI may provide the first document and chat interface, but it must not own the library, workflows, memory, embeddings, or model configuration. It should be replaceable without losing Atelier data.

### 4. Explicit workflow harness — LangGraph later

The intended workflow shape is:

```text
input → characterize → route → retrieve → select tools → reason
      → verify → escalate if necessary → answer
```

LangGraph is a candidate for explicit, stateful workflows that combine deterministic code, LLM-controlled steps, persistence, and human intervention. Start with simple workflows and add complexity only when the need is demonstrated.

Do not begin with a giant autonomous-agent framework or many agents talking to one another.

### 5. Tools

Tools make local models useful. They should be exposed gradually and guarded by explicit permissions.

Initial tool families:

- **Files:** list, read, search, copy/move, metadata;
- **Papers:** PDF text, metadata, tables, figures, OCR;
- **Code:** Git, ripgrep, Python, tests, compilers, linters;
- **Data:** CSV, JSON, Parquet, SQLite, spreadsheets;
- **Research:** DOI, arXiv, Crossref, Semantic Scholar, web search;
- **Quantum:** Qiskit, circuit inspection, transpilation, simulation, resource counting;
- **Optimization:** Gurobi, OR-Tools, SciPy, CVXPY, solution validation.

MCP should be the connector standard where practical, allowing the same paper-library or domain tool to be used by Atelier, Claude, Gemini, and other compatible clients.

### 6. Local research memory

Research memory should remain outside the UI layer:

```text
~/Atelier/
├── library/
│   ├── papers/
│   ├── books/
│   ├── notes/
│   ├── datasets/
│   └── code/
├── database/
│   ├── metadata.sqlite
│   └── vectors/
├── workspace/
├── models/
└── config/
```

Use SQLite for metadata and LanceDB as a candidate embedded vector/full-text store. Keep original files, extracted text, metadata, chunks, and embeddings separately so the storage layer can evolve without losing sources.

## Local model roles

The five local roles are deliberately distinct:

1. **Tiny worker/router, approximately 2–4B:** classification, metadata, JSON, query rewriting, tool choice, RAG filtering, and cheap repetitive reasoning.
2. **Embedding model:** semantic search and retrieval; it does not need to chat.
3. **Small coding model, approximately 7–14B:** repository exploration, scripts, tests, debugging, and small refactors.
4. **Multimodal/document model, approximately 4–12B:** figures, diagrams, plots, screenshots, tables, slides, and scanned pages.
5. **Large local reasoner, approximately 20–30B Q4:** mathematics, paper analysis, optimization, quantum reasoning, complex code, synthesis, and private intellectual work.

These roles map onto the four-tier stack in the root README: the embedding model is infrastructure, while the tiny worker, coding model, and large local reasoner occupy the main model tiers. A multimodal model is added only when document/figure evaluation justifies it.

Do not fine-tune Atelier-specific models until the workflows have produced useful, high-quality training data.

## First-generation download roster

Do not fill the machine with overlapping models. The first local stack is four downloads now, with a fifth slot reserved for the future large reasoner.

| Role | Model and quantization | Approx. disk | Purpose | Why this choice |
|---|---|---:|---|---|
| Tiny worker/router | `LFM2.5-2.6B` `Q6_K` | 2.22 GB | Routing, extraction, structured JSON, tool selection, query rewriting, fast characterization, and repetitive local actions | Small enough to run frequently while retaining more precision than an aggressive Q4 quantization; designed for on-device agent workloads |
| Embeddings/search | `qwen3-embedding:4b` `Q4_K_M` via Ollama | ~2.5 GB | 2,560-dimensional semantic search across papers, notes, code, extracted text, and experiments | This is the validated Step 2 retrieval backend; instruction-aware query formatting improved direct scientific relevance on the Atelier benchmark |
| Coding specialist | `Ornith-1.0-9B` `Q5_K_M` | 6.47 GB | Repository exploration, scripts, debugging, tests, terminal-agent work, and small refactors | Coding-focused agentic training makes it a better candidate for acting on repositories than a general-purpose reasoner; Q5 balances coding quality and memory |
| Vision/document | `Qwen3-VL-8B-Instruct` `Q4_K_M` | 6.1 GB | Figures, diagrams, screenshots, tables, scanned pages, visual equations, and OCR fallback | Scientific-document focus, visual reasoning, OCR, and long-document structure at a manageable local size; normal PDFs should use native text parsing first |
| Main local reasoner | `Qwen3.8-27B`, probably Q4-class | Reserve 25 GB | Mathematics, paper analysis, optimization, quantum reasoning, private documents, complex coding, and synthesis | This is the regular-use upper range for a 36 GiB M3 Pro; wait for official weights and compare GGUF Q4, MLX 4-bit, and possibly Q5 on the actual Mac |

### Storage policy

The four immediate downloads total approximately 15.43 GB. Reserve another 25 GB for the future Qwen3.8-27B slot rather than treating all remaining disk space as model capacity. Python environments, Hugging Face caches, research datasets, vector stores, Docker images, and fine-tuning artifacts also need room.

### Installation policy

Install and understand one model at a time:

1. install `LFM2.5-2.6B` alone;
2. measure speed, memory, structured extraction, tool-call formatting, and paper classification;
3. install the validated `qwen3-embedding:4b` backend and benchmark retrieval;
4. install Ornith and evaluate repository tasks;
5. install Qwen3-VL and evaluate figures, tables, screenshots, and OCR fallback;
6. wait for the official Qwen3.8-27B weights before filling the large-reasoner slot.

Do not keep all large models loaded simultaneously. Unified memory, not disk, is the main constraint. The router should load the large reasoner only for hard work, then unload it when the task is complete. Use retrieval and chunking rather than enormous context windows by default.

### Deliberately deferred

- `LFM2.5-8B-A1B`: overlaps the tiny worker and future large-reasoning roles;
- Gemma 4 12B: interesting multimodal model, but overlaps the document tier initially;
- Qwen3-Embedding-8B: defer until a retrieval benchmark demonstrates that 4B is insufficient;
- `LFM2.5-ColBERT-350M`: revisit when late-interaction retrieval is being implemented;
- dedicated OCR models: Qwen3-VL is the first baseline;
- 70B+ models: frontier subscriptions cover that tier more effectively.

## Cloud responsibilities

Cloud models must remain optional and complementary:

- **Claude:** architect, critic, reviewer, mathematical reasoning partner, research planner, difficult debugger;
- **Codex:** implementation engineer, repository modifier, test runner, refactoring and experiment agent;
- **Gemini:** very large context, multimodal material, large document sets, figures/screenshots, independent second opinions, and Google workflows.

Initially preserve native subscription workflows. Do not add API-based automatic routing or LiteLLM until explicit automatic cloud routing is needed.

## Interfaces and privacy

Provide three interfaces over one backend:

1. a web UI for chat, documents, images, research, and the library;
2. an `atelier` CLI for commands such as `ask`, `paper`, `inspect`, `search`, `compare`, and `summarize`;
3. Finder actions for characterize, summarize, add to library, explain, and ask about.

Every task should support a privacy mode:

- **LOCAL ONLY:** no cloud escalation;
- **CLOUD ALLOWED:** frontier escalation is permitted after the workflow decides it is useful.

Private and unpublished research should default to local-only handling.

## What we are not building

- a ChatGPT clone;
- a thin wrapper around Ollama;
- a coding-only agent;
- twenty agents talking to one another;
- a RAG demo with no durable library;
- a large collection of downloaded models;
- an autonomous agent with unrestricted access to the Mac.

The target is a **local-first, model-agnostic, tool-using personal AI workbench that understands the Mac, its files, and the research workflow, with cloud intelligence available only when useful**.

## Build order

1. local model foundation;
2. choose and benchmark the small model set;
3. add Open WebUI as a replaceable front end;
4. implement fast PDF characterization;
5. create the local research library;
6. add semantic search/RAG;
7. add general file characterization;
8. add code/folder characterization;
9. expand the deterministic tool layer;
10. introduce explicit LangGraph workflows;
11. add automatic task routing;
12. integrate durable memory;
13. add Finder integration;
14. add the CLI workflows;
15. add Claude/Codex/Gemini handoff;
16. benchmark models and harnesses;
17. fine-tune local components;
18. add more sophisticated agents only when justified.

## Immediate next step

Decide the exact local roster for the M3 Pro with 36 GB unified memory before installing more models:

1. tiny worker/router;
2. embedding model;
3. coding model;
4. multimodal/document model;
5. large reasoning model.

Select one candidate per role, calculate storage and memory implications, install one at a time, and evaluate what each model can and cannot do before building the UI or harness.
