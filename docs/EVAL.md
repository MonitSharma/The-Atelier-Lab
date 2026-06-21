# Atelier — reliability evaluation

This is the honest, reproducible reliability writeup the project is built around
(PROJECT.md §9–§10). It reports how often the local agent succeeds at each mode,
on frozen task suites, with the exact setup so the numbers can be reproduced and
tracked over time.

## How to reproduce

```bash
source .venv/bin/activate
atelier eval                 # both suites
atelier eval --judge         # add local LLM-as-judge for groundedness
```

Reports are written to `data/eval_reports/report_*.json`.

## Setup

| | |
|---|---|
| Brain model | `qwen3:14b` (Ollama, 4-bit) |
| Embeddings | `BAAI/bge-base-en-v1.5` (768-dim, MPS) |
| Retrieval k | 6 |
| Hardware | MacBook M3 Pro, 36 GB |
| Suites | `eval/tasks_docqa/` (6 Qs), `eval/tasks_code/` (2 tasks) |

## Baseline results — 2026-06-21

### Knowledge mode (doc-QA, 6 questions over the real corpus)

| Metric | Score |
|---|---|
| Correct (keyword coverage ≥ 0.5) | **100%** (6/6) |
| Retrieval hit@6 (expected source retrieved) | **100%** (6/6) |
| Cited sources | **100%** (6/6) |

### Build mode (code, 2 fix-the-failing-test tasks)

| Task | Solved | Steps | Tool errors |
|---|---|---|---|
| add_bug (arithmetic) | ✅ | 5 | 0 |
| offbyone (slice off-by-one) | ✅ | 6 | 0 |
| **Overall** | **100%** (2/2) | avg 5.5 | 0.0 |

Total wall-clock for the full run: ~3 min.

## Honest caveats (read these)

These are **strong baseline numbers on a small, deliberately tractable suite** —
they are a starting point, not a claim of general reliability:

- **Suite size is tiny** (6 + 2). 100% here means "no obvious failures on easy
  cases," not "reliable on hard ones." The next work is *expanding difficulty*:
  multi-hop questions, ambiguous retrieval, multi-file bugs, tasks needing
  several coordinated edits.
- **doc-QA "correct" is keyword-based** — a coarse proxy. Run `--judge` to add
  the local LLM-as-judge (correctness + groundedness); treat the judge as
  advisory, since a small local judge is itself fallible.
- **Code tasks are single-bug, single-file.** Real reliability pressure comes
  from error compounding across many steps (PROJECT.md §3, §11) — not yet probed.
- **Determinism:** temperature is 0.1, not 0. Re-runs can vary slightly; the
  saved reports let you spot regressions across runs.

## What this proves so far

A fully local, $0, laptop-sized agent **reliably**:
1. answers questions grounded in the user's own documents, with correct
   retrieval and citations; and
2. fixes a failing test across a multi-step tool-using run, **proving** the fix
   with a green test — with zero tool errors on these tasks.

## Next on the eval roadmap

- Grow both suites and stratify by difficulty; plot success vs. difficulty (the
  "one clear figure" of PROJECT.md §10).
- Add a regression gate: `atelier eval` compares against the last saved report
  and flags any drop.
- Add combined knowledge→build tasks (retrieve from notes, then make a verified
  code change) to the code suite.
