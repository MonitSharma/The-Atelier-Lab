# How far can a fully local, zero-cost agent go on one laptop?

*A reliability study of Atelier — a dual-mode (knowledge + build) AI agent that
runs entirely on a MacBook M3 Pro (36 GB), at $0, with no cloud APIs.*

## Abstract

Atelier is a single agent harness with two modes: **knowledge** (retrieval-
augmented Q&A over the user's own documents) and **build** (read a repo, edit
code, run tests, fix failures). It runs on local models via Ollama (`qwen3:14b`
brain, `qwen3:4b` worker), a local embedding model, a local vector store, and a
locally **LoRA-fine-tuned 0.5B router** that sends easy subtasks to the cheap
model. We evaluate it on frozen task suites and report where it works and where
it breaks. The headline: a laptop-sized agent answers corpus questions reliably,
fixes simple bugs with test-verified changes, and a tiny fine-tuned router
recovers from 44% to 100% accuracy on difficulty classification — while honestly
hitting a reasoning ceiling on multi-line structural code edits.

## 1. The question

Not "can we beat Claude/Cursor" (we can't, and don't try). The question is the
*frontier of local-only*: with a model small enough to run on one laptop, how
reliable is an agent at (a) using your knowledge and (b) acting on your code —
and where exactly does it fail? That boundary is the result.

## 2. System (one paragraph)

One ReAct loop drives a shared toolbox (semantic note search, file read/write/
edit, sandboxed code exec, a pytest runner, repo map, memory). Knowledge mode
fuses dense + BM25 retrieval (RRF) with optional cross-encoder reranking; build
mode proves every change with a green test run. A fine-tuned 0.5B classifier
routes easy tasks to the worker model. Everything is local; the only network use
is the Ollama endpoint and one-time model downloads. Full design:
[`docs/ARCHITECTURE.md`](ARCHITECTURE.md).

## 3. Method

- **Models:** brain `qwen3:14b` (4-bit), worker `qwen3:4b`, embeddings
  `bge-base-en-v1.5`, router `Qwen2.5-0.5B` + LoRA.
- **Baseline suites:** 8 doc-QA questions over the real corpus; 3 build tasks
  (repo + bug + hidden test). Metrics: keyword-coverage correctness, retrieval
  hit@k, citation rate (knowledge); solved / steps / tool-errors (build).
  The repo now also contains an expanded 18 doc-QA + 13 code-task suite for the
  next reliability curve.
- **Router fine-tune:** 256 synthetic difficulty-labeled examples, LoRA on 0.5B,
  200 iters (~1 min, peak 1.5 GB). Held-out test accuracy, base vs. adapted.
- **Honesty rules:** suites are frozen; we report failures; no tuning-to-pass.

## 4. Results

### 4.1 Knowledge mode
| Metric | Score |
|---|---|
| Correct (8 questions) | **100%** (8/8) |
| Retrieval hit@k | **100%** (8/8) |
| Citation rate | **75%** (6/8) |

Retrieval and answer correctness are saturated on this corpus; the only gap is
citation discipline (2/8 answers were right but dropped the `[n]` markers).

### 4.2 Build mode
| Task | Solved | Steps |
|---|---|---|
| add_bug (single-line arithmetic) | ✅ | 5 |
| offbyone (single-line slice) | ✅ | 6 |
| median_bug (multi-line if/else) | ❌ | 12 (budget) |
| **Overall** | **67%** (2/3) | avg 7.7 |

**The failure is the finding.** `median_bug` needs replacing one line with a
multi-line `if/else`. `qwen3:14b` is unreliable here: once it wrote correct logic
but mis-indented it (`return` outside the function → `SyntaxError`); another run
never landed a working edit within budget. Single-line fixes: reliable.
Structural multi-line edits: not, at this model size. This drove a real product
fix — the edit/write tools now run a `compile()` check and report `syntax_ok`, so
the agent is told the instant it breaks a file.

### 4.3 The fine-tuned router (model-as-component)
| | Accuracy (held-out) |
|---|---|
| Base 0.5B (zero-shot) | **43.8%** |
| + LoRA fine-tune | **100%** |
| **Lift** | **+56.2 pts** |

The fine-tune takes a 0.5B model from worse-than-chance to a perfect in-
distribution router, and it **generalizes to novel phrasings** not in the
training templates (e.g. "Track down an intermittent deadlock that spans the
worker pool and the DB layer" → hard; "Uppercase a string" → easy).

### 4.4 Routing savings
On the 8-question doc-QA workload, the fine-tuned router sent **4/8 to the cheap
worker** and 4/8 to the brain:

| | value |
|---|---|
| Brain calls saved | **50%** (4/8) |
| Routed accuracy | **100%** |
| Always-brain accuracy | 100% |

Routing **halved brain calls with zero accuracy loss**. In fact the worker (4B)
answered all 8 correctly here, so the router is *conservative* — it sent some
answerable questions to the brain. That's the safe failure mode: under-routing
costs a little speed; over-routing would cost correctness. The realistic takeaway
is that a 1-minute fine-tune of a 0.5B model meaningfully cuts the cost of the
agent without hurting it.

### 4.5 One figure: where the local agent stands

```
 correctness / reliability  (higher = better)
 doc-QA correct      ██████████████████████  100%
 doc-QA retrieval    ██████████████████████  100%
 doc-QA citation     ████████████████▌       75%
 router (finetuned)  ██████████████████████  100%
 router (base)       █████████▋              44%
 build: single-line  ██████████████████████  100%
 build: multi-line   ░░░░░░░░░░░░░░░░░░░░░░    0%   <- the reasoning ceiling
```

## 5. Honest limitations

- **Small recorded baseline** (8 + 3). 100% on knowledge means "no obvious
  failures on a modest corpus," not "robust at scale." The expanded suite is in
  the repo; the next step is running it and reporting success by difficulty.
- **In-distribution router test.** 100% reflects pattern learning on templated
  data; the novel-phrasing spot-checks are encouraging but not a generalization
  benchmark.
- **Keyword-based correctness** is coarse; the optional local LLM-judge
  (`--judge`) gives a second, also-fallible opinion.
- **One model size.** The build-mode ceiling is for `qwen3:14b`; `--heavy`
  (`gemma4:26b`) is untested on the hard task.

## 6. Conclusion

A fully local, $0, single-laptop agent is genuinely useful today: it answers
grounded questions over your notes and makes test-verified single-step code
fixes, with persistent memory and an MCP interface other tools can call. Its
honest limits are (a) structural multi-line code edits and (b) corpus/suite
scale — both measured here, not hidden. A 1-minute LoRA fine-tune of a 0.5B model
yields a usable router, demonstrating the "small model as a cheap component"
pattern at the smallest possible scale.

## 7. Reproduce it

```bash
make reproduce        # env → models → tests → eval → train+eval router
# or step by step:
make test && make ingest && make eval && make train-router && make route-eval
```

Artifacts: the frozen suites (`eval/`), the trained adapter
(`models/router/adapter/`), JSON reports (`data/eval_reports/`), and per-run
traces (`data/traces/`). Reliability details: [`docs/EVAL.md`](EVAL.md).
