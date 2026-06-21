# Atelier

A fully **local**, **zero-cost**, **dual-mode** AI agent that runs on a single
MacBook (Apple Silicon, 36 GB). It does two things over one shared harness:

- **Knowledge mode** — ask questions grounded in *your own* notes, PDFs, and
  code (local RAG). Your documents never leave the machine.
- **Build mode** — read a repo, edit code, run tests, and fix failures, proving
  each change with a green test run.

No cloud APIs, no subscriptions, no rented GPUs. Everything runs against a local
[Ollama](https://ollama.com) server and a local embedding model.

> Design rationale, scope, and roadmap live in [`PROJECT.md`](PROJECT.md).

## Requirements

- macOS on Apple Silicon (built/tested on M3 Pro, 36 GB)
- [Ollama](https://ollama.com) running locally (`ollama serve`)
- Python 3.11+ and [`uv`](https://github.com/astral-sh/uv)
- Models pulled locally:
  ```bash
  ollama pull qwen3:14b   # brain (reasoning / build)
  ollama pull qwen3:4b    # fast worker / router
  ollama pull gemma4:26b  # optional heavy reasoner
  ```

## Setup

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .            # provides the `atelier` command
atelier doctor                 # verify models + store + embeddings
```

## Knowledge mode — quickstart

```bash
# 1. Index your notes (point it anywhere — an Obsidian vault, a papers folder…)
atelier ingest ~/Notes ./Project.md

# 2. Ask, grounded in what you indexed
atelier ask "What did I decide about the embedding model and why?"

# 3. Or chat interactively
atelier chat
```

Useful flags: `atelier ask -k 8 --show-context "<q>"` (more context, show
passages), `--heavy` (use the larger reasoning model), `atelier sources` (list
what's indexed), `atelier ingest --reset <path>` (rebuild the index).

## Build mode — the autonomous agent

The full dual-mode agent reasons and uses tools (file read/write/edit, repo map,
sandboxed code exec, pytest runner, semantic note search) to complete tasks:

```bash
atelier tools                              # see the toolbox
atelier agent "Fix the failing test in sample_task/ and prove it passes"
atelier agent "Using my notes, summarize the project's non-goals" 
```

Each run streams its steps and writes a full trace to `data/traces/`. Add
`--shell` to enable the (powerful, lightly-guarded) shell tool, `--heavy` for the
bigger model, `--max-steps N` to bound the loop.

## Testing

A complete, ability-by-ability test playbook lives in
[`docs/TESTING.md`](docs/TESTING.md). The fast automated suite:

```bash
pytest -q        # 40+ tests, no model required
```

## Reliability evaluation

Atelier ships frozen task suites and a scored eval harness — the part that makes
it a *measured* system, not just a demo:

```bash
atelier eval                 # score both modes, save a JSON report
atelier eval --judge         # add a local LLM-as-judge for groundedness
```

Current baseline (M3 Pro, `qwen3:14b`): **doc-QA 6/6 correct, code 2/2 solved**.
Full results, setup, and honest caveats in [`docs/EVAL.md`](docs/EVAL.md).

## Configuration

Everything is overridable via environment variables (prefix `ATELIER_`) or a
`.env` file. See [`atelier/config.py`](atelier/config.py). Common knobs:

| Variable | Default | Meaning |
|---|---|---|
| `ATELIER_BRAIN_MODEL` | `qwen3:14b` | main reasoning model |
| `ATELIER_EMBED_MODEL` | `BAAI/bge-base-en-v1.5` | local embedding model |
| `ATELIER_RETRIEVAL_K` | `6` | chunks retrieved per query |
| `ATELIER_CHUNK_SIZE` | `1000` | chunk size (characters) |

## Layout

```
atelier/   config + CLI
agent/     ReAct loop, brain (Ollama client), memory
tools/     tool registry + individual tools (calculator, file read, …)
rag/       knowledge mode: ingest → chunk → embed → store → retrieve → answer
eval/      reliability harness (frozen task suites)   [planned]
docs/      design notes and the eventual writeup
```

## License

Apache-2.0.
