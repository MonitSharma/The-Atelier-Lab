# Atelier — reliability evaluation

This is the honest, reproducible reliability writeup the project is built around
(PROJECT.md §9–§10). It reports how often the local agent succeeds at each mode,
on frozen task suites, with the exact setup so the numbers can be reproduced and
tracked over time.

## How to reproduce

```bash
source .venv/bin/activate
atelier eval                 # all suites
atelier eval --mode combined # knowledge -> build composition only
atelier eval --judge         # add local LLM-as-judge for groundedness
atelier eval-plots           # SVG plots from the latest saved report
```

Reports are written to `data/eval_reports/report_*.json`.
Plots are written to `data/eval_reports/plots/<report-name>/`.

## Setup

| | |
|---|---|
| Brain model | `qwen3:14b` (Ollama, 4-bit) |
| Embeddings | `BAAI/bge-base-en-v1.5` (768-dim, MPS) |
| Retrieval k | 6 |
| Hardware | MacBook M3 Pro, 36 GB |
| Suites | `eval/tasks_docqa/` (18 Qs), `eval/tasks_code/` (13 tasks), `eval/tasks_combined/` (10 tasks) |

## Latest expanded runs — 2026-06-21/22 UTC

| Metric | Score |
|---|---|
| Knowledge correctness | **94%** (17/18) |
| Knowledge retrieval hit@k | **83%** (15/18) |
| Knowledge citations | **100%** (18/18) |
| Code solved after path fix | **100%** (13/13) |
| Combined solved | **100%** (10/10) |
| Combined used `search_notes` | **100%** (10/10) |
| Average code steps after path fix | **6.1** |
| Average tool errors after path fix | **0.0** |

Plots from this run are checked into `docs/assets/eval/report_20260621T173650/`
and embedded in the README.

### Knowledge mode

The model answered 17/18 questions correctly and cited sources on all 18
answers. The only incorrect task in this run was `median-failure-finding`.

Retrieval hit@k improved from 61% to 83% after the metric was updated to allow
multiple valid expected sources for facts repeated across README, Project.md,
and docs files.

### Build mode

| Slice | Solved | Steps | Tool errors |
|---|---:|---:|---:|
| All code tasks | **100%** (13/13) | 6.1 | 0.0 |
| Easy tasks | **100%** | 5.6 | 0.0 |
| Medium tasks | **100%** | 6.2 | 0.0 |
| Single-line edits | **100%** | 5.6 | 0.0 |
| Multi-line edits | **100%** | 6.2 | 0.0 |

Every category now solves at 100% on the 13-task code suite, including
`structural_logic`.

This is the clearest current finding: **the prior failure was not only a model
reasoning limit; a path-handoff bug between `repo_map` and file tools was a major
cause.** Once `repo_map` emitted workspace-relative paths, `median_bug` passed
and the full code suite reached 100%.

### Post-eval fix

After the 92% full run, two fixes were added:

- `repo_map` now emits workspace-relative paths, so the agent can copy paths
  directly into `read_file`, `edit_file`, and `ast_edit`.
- `ast_edit` can replace Python function bodies with a compile check before
  writing.

A targeted live rerun of `median_bug` passed in 5 steps with 0 tool errors.
Then the full 13-task code suite passed:

```text
code solved: 100%
average steps: 5.8
average tool errors: 0.0
report: data/eval_reports/report_20260621T171954.json
```

The latest full all-mode report is:

```text
data/eval_reports/report_20260621T173650.json
```

### Combined mode

The combined knowledge→build suite passed on the full 10-task run:

| Metric | Score |
|---|---:|
| Solved | **100%** (10/10) |
| Tests passed | **100%** (10/10) |
| Used `search_notes` | **100%** (10/10) |
| Average steps | **6.7** |
| Average tool errors | **0.0** |

Report:

```text
data/eval_reports/report_20260622T011056.json
```

Plots:

```text
docs/assets/eval/report_20260622T011056/
```

The first 10-task run scored 9/10 because `router_policy` exposed a
mixed-indentation edge case in `ast_edit`. The model proposed reasonable logic,
but the function body it sent had one extra indentation level on later sibling
lines. `ast_edit` now tries safe normalizations and writes only a candidate that
keeps the whole Python file compile-valid. After that fix, `router_policy`
passed in a targeted rerun and the full combined suite passed 10/10.

## Smaller baseline — 2026-06-21 (8 doc-QA + 3 code)

The earlier baseline was intentionally smaller:

| Suite | Result |
|---|---:|
| Doc-QA correctness | **100%** (8/8) |
| Retrieval hit@k | **100%** (8/8) |
| Citation rate | **75%** (6/8) |
| Code solved | **67%** (2/3) |

The expanded run is more informative than this baseline: it shows that build
mode is stronger across simple repairs than the 3-task suite suggested, while
confirming the same hard boundary around structural multi-line edits.

## Expanded suite — added 2026-06-22

The current frozen suite is larger than the recorded baseline:

| Suite | Count | Coverage |
|---|---:|---|
| Doc-QA | 18 | constraints, architecture, RAG, tools, models, usage, evaluation |
| Code repair | 13 | arithmetic, off-by-one, normalization, mutation, order preservation, structural logic |
| Combined | 10 | retrieve a project/user decision, then make a verified code change |

The code tasks now include task metadata:

| Field | Meaning |
|---|---|
| `category` | bug family, e.g. `off_by_one`, `normalization`, `structural_logic` |
| `difficulty` | coarse label: `easy` or `medium` |
| `edit_scope` | expected repair shape: `single_line` or `multi_line` |

`eval/run_eval.py` includes grouped aggregates under `by_category`,
`by_difficulty`, and `by_edit_scope`, which is the basis for the reliability
curve: success rate vs. task type/difficulty. Run `atelier eval --mode all` to
generate a new report under `data/eval_reports/`, then run `atelier eval-plots`
to generate charts for that report.

Combined tasks are stricter than normal code tasks: they require both a clean
test run and `search_notes` appearing in the agent trace.

### Router (Phase 6) — fine-tuned cheap component

A LoRA fine-tune of `Qwen2.5-0.5B` (256 synthetic examples, 200 iters, ~1 min,
peak 1.5 GB) as a task-difficulty classifier:

| | Held-out accuracy |
|---|---|
| Base 0.5B (zero-shot) | 43.8% |
| + LoRA fine-tune | **100%** |
| Lift | **+56.2 pts** |

Routing on the doc-QA workload (`python -m eval.route_eval`):

| | value |
|---|---|
| Brain calls saved | **50%** (4/8 routed to the 4B worker) |
| Routed accuracy | 100% |
| Always-brain accuracy | 100% |

→ Half the brain calls eliminated with no accuracy loss. The router is
conservative (the worker could actually answer all 8), which is the safe
direction. Caveat: the held-out router test is in-distribution (templated);
novel-phrasing spot-checks pass but aren't a generalization benchmark.

Reproduce: `make train-router && make route-eval`.

## Honest caveats (read these)

These are **strong baseline numbers on deliberately tractable suites** — they
are a starting point, not a claim of general reliability:

- **The current suites are still modest** (18 doc-QA + 13 code + 10 combined).
  100% on a slice means "no failures on this frozen suite," not "reliable on
  hard open-ended tasks."
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
   with a green test — with zero tool errors on these tasks; and
3. composes those modes by retrieving a project decision, editing code from that
   decision, and proving the result with tests.

## Next on the eval roadmap

- Train and evaluate the planner-router adapter from the 41-row eval-derived
  dataset.
- Add harder multi-file combined tasks where retrieved notes affect more than
  one module.
- Track repeated-run variance for the live local model, not only one successful
  report.
