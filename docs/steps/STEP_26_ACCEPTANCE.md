# Step 26 — Deterministic acceptance and release

`atelier acceptance` runs an offline acceptance smoke across package readiness,
service/workspace state, workflows, QASM and optimization tools, security
policy, network denial, web UI, registry dispatch, Finder planning, handoff
creation, project memory, and runtime recovery. It reports every check instead
of stopping at the first failure.

`atelier acceptance --clean` additionally creates a fresh temporary `Atelier`
home and workspace, profiles a structured file, characterizes a real paper
fixture, persists an approval-gated workflow, reconstructs the service from
disk, resumes it, and verifies local-only research denial. This is the
model-free clean-state evidence; it does not claim live model answer quality.

The release checklist also runs the full pytest suite, `atelier package check`,
`atelier reliability --suite v2`, `atelier performance`, and runtime export/
restore checks. Model-backed paper ingestion/answering, optional Qiskit
capabilities, hardware performance collectors, and real external handoff remain
explicitly operator-controlled; the release does not pretend to have verified
them with the local offline smoke.

## Latest live local evidence

The installed `qwen3:8b` model was used for a real retrieval → local inference
run over the verified external library:

```bash
ATELIER_BRAIN_MODEL=qwen3:8b atelier ask --show-context \
  "What is the main decision-relevant claim of Q-SHIELD, and why does it matter for quantum tail-risk estimation in logistics?"
```

The run retrieved `qshield.pdf` and `tail_risk.pdf` and returned the correct
decision-relevant criterion: common-mode bias does not change policy ranking,
while differential bias can; it also preserved the paper's caution that this
does not establish quantum advantage. This is live model evidence, but the
full clean install, fresh ingestion, and model-backed repository-edit scenario
remain separate release evidence before Step 26 is marked complete.
