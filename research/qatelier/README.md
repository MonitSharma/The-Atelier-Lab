# QAtelier evaluation set

This is a small, repeatable evaluation set for the local Atelier workflow using
the private source document:

`~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx`

The source document is intentionally not copied into this repository. Ingest it
locally before running the evaluation:

```bash
ATELIER_BRAIN_MODEL=qwen3:8b atelier ingest \
  ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
```

The eight questions in [`questions.json`](questions.json) test the useful research
behaviours rather than generic fluency:

- summary: preserve the research objective and contribution without inflating the claim;
- assumptions: expose representation, compression, parameter-matching, data, and hardware assumptions;
- methods: reconstruct the comparison ladder and experimental protocol;
- risks: identify confounders, failure modes, and meaningful falsifiers;
- citations: separate claims supported by the plan from claims requiring external verification;
- equations: transcribe and explain equations without silently correcting uncertainty;
- embedded visuals: describe diagrams or document images and abstain when none are present;
- proposed experiments: turn the plan into a dependency-ordered first experiment sequence.

## Scoring rubric

Score each question from 0 to 2:

- **0 — unusable:** misses the requested dimension, invents details, or cannot be traced to the source;
- **1 — partial:** directionally correct but incomplete, weakly grounded, or vague about controls;
- **2 — research-useful:** accurate, appropriately qualified, source-grounded, and actionable.

Record the score, model name, model size/quantization, retrieval settings, and
whether the answer used only QAtelier or additional sources. A strong result is
not merely a high total: the answer must not call something a quantum advantage
without parameter-matched classical baselines, held-out evaluation, resource
accounting, and hardware-aware evidence.

## Running one question

```bash
atelier ask --show-context \
  "Use the QAtelier document. What assumptions does it make about frozen representations, compression, parameter matching, data regimes, and hardware execution? Distinguish explicit assumptions from your inferences."
```

For a clean QAtelier-only run, use a temporary Atelier home, ingest only this
document there, and then ask the questions. This avoids unrelated papers in the
normal knowledge base influencing the evaluation:

```bash
qatelier_home="$(mktemp -d /tmp/atelier-qatelier-eval.XXXXXX)"
ATELIER_HOME="$qatelier_home" atelier ingest \
  ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
ATELIER_HOME="$qatelier_home" atelier ask --show-context \
  "Give a concise, faithful summary of the QAtelier research plan, its proposed contribution, and the evidence required before claiming quantum advantage."
```

Delete the temporary directory after inspection if desired; it contains only
the derived local index, not the original document.
