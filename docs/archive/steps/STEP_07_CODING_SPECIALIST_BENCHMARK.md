# Step 07 — Coding Specialist Benchmark

Status: **complete**

## Decision

The dedicated `coder` role is configured as:

```text
qwen3:8b
```

It is the best balanced 7–14B candidate in this first frozen run: it solved all
three multi-file tasks, produced no tool errors or invalid edits, and was faster
than Gemma 4 12B. It is a role assignment, not a claim that Qwen3 8B is the
best coding model for every repository or future model release.

## Frozen workload

The benchmark lives in `atelier_agent/eval/tasks_coding_specialist/` and runs
each candidate in a clean isolated copy. Every task requires repository mapping,
source/test inspection, edits, and a final independent pytest verification:

- `config_pipeline`: configuration immutability plus filtering/limiting across
  modules;
- `records_report`: normalization, inclusive threshold behavior, and empty
  input handling across modules;
- `query_service`: case-insensitive multi-module query behavior and limits.

The benchmark command is:

```bash
ATELIER_NO_BANNER=1 atelier benchmark-coding --model MODEL --max-steps 8
```

## Results

All numbers below are means across the three tasks. The run used the same
prompts, tools, eight-step cap, temperature, and independent pytest verifier.

| Candidate | Size in Ollama | Solve/test pass | Unnecessary reads | Invalid edits | Tool errors | Mean latency | Prompt tokens | Completion tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LFM2.5 worker | 2.2 GB | 1/3 | 0.0 | 0.0 | 0.333 | 94.8 s | 24,282 | 4,196 |
| Qwen2.5-Coder 7B | 4.7 GB | 0/3 | 0.0 | 0.0 | 0.0 | 34.5 s | 29,795 | 588 |
| Gemma 4 12B Q4 | 7.6 GB | 3/3 | 0.0 | 0.333 | 0.333 | 70.6 s | 25,924 | 734 |
| **Qwen3 8B** | **5.2 GB** | **3/3** | **0.0** | **0.0** | **0.0** | **42.9 s** | **27,006** | **682** |
| Gemma 4 26B heavy reference | 17 GB | 3/3 | 0.0 | 1.333 | 1.0 | 37.8 s | 32,254 | 767 |

The worker and Qwen2.5-Coder runs were measured with the same eight-step cap in
the final comparison records. An earlier six-step worker run exposed the
expected budget sensitivity but is not used in the table.

## Measurement notes

- `solve/test pass` is an objective pytest result, not a language-model judge.
- `unnecessary reads` counts `read_file` calls outside the task's declared
  relevant files; repository maps and the task's own test file are not treated
  as unnecessary.
- `invalid edits` counts edit-tool failures or syntax-invalid edit results.
- `tool errors` counts any failed tool observation.
- Latency is wall-clock time for the agent run and final verification.
- Prompt/completion tokens come from Ollama response telemetry.
- Peak process RSS is recorded in each JSON report. It is not the full unified
  memory footprint because Ollama serves the model in a separate process;
  host-level residency sampling is deliberately deferred to Step 24.

## Model-selection rationale

The candidate set was selected at execution time from models currently exposed
by Ollama. Qwen2.5-Coder is an explicit coding-specialist control, Qwen3 8B is
a general 8B control, Gemma 4 12B is a current agentic/coding-capable model,
and Gemma 4 26B is the installed heavy reference. The official Ollama catalog
lists Qwen2.5-Coder in 7B and 14B sizes, Qwen3 in 8B and 14B sizes, and Gemma 4
12B/26B variants with coding and agentic-workflow support.

## Follow-up

Step 08 should wrap this role in the typed inspect → plan → edit → test → diff
certificate workflow. The benchmark remains a regression gate; it should be
expanded with larger repositories and repeated trials under Step 23.

## Current-catalog revalidation

The candidate choice was rechecked against the current primary model pages
before the clean-state release run. The official [Qwen3-8B model
card](https://huggingface.co/Qwen/Qwen3-8B), [Qwen2.5-Coder Ollama
catalog](https://ollama.com/library/qwen2.5-coder), and [Google Gemma 4 model
card](https://ai.google.dev/gemma/docs/core/model_card_4) still describe the
families used in this comparison as coding/agentic-capable local candidates.
This does not replace rerunning the frozen benchmark when a new candidate is
considered.
