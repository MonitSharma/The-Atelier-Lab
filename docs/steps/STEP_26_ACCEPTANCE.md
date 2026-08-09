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
model-free clean-state evidence; live local-model answer and code quality are
recorded separately in
[`STEP_26_ATELIER_V1_RELEASE.md`](STEP_26_ATELIER_V1_RELEASE.md).

The release checklist also runs the full pytest suite, `atelier package check`,
`atelier reliability --suite v2`, `atelier performance`, and runtime
validation. Model-backed paper ingestion/answering and repository editing have
now been verified in the isolated local run; optional Qiskit capabilities,
hardware performance collectors, and real external handoff remain explicitly
operator-controlled.

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
does not establish quantum advantage. Fresh-runtime model-backed paper and
repository evidence is summarized in the v1.0 release document.
