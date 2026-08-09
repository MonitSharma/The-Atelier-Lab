# Atelier v1.0 — Release evidence

Status: **verified local release evidence**

This document records the evidence for the clean-state Atelier v1.0 scenario.
The evidence is split into deterministic model-free checks and isolated local
model runs so neither is mistaken for the other.

## End-to-end scenario

The fresh-runtime run was executed in a temporary `ATELIER_HOME` and temporary
approved workspace:

1. `atelier init` created a new versioned runtime home.
2. A workspace was attached with `read`, `write`, and `execute` capabilities
   under `LOCAL_ONLY`.
3. `qshield.pdf` was characterized and freshly embedded into a new 2,560D
   index containing 89 chunks.
4. Qwen3-8B retrieved the new local passages and answered with citations,
   preserving the paper's explicit “no quantum advantage” limitation.
5. A separate fresh repository was inspected and repaired by the Qwen3-8B
   coder workflow. The independent test run passed and the certificate listed
   only `calculator.py` as changed.
6. The deterministic clean acceptance scenario profiled CSV data, rendered
   scientific figure evidence, ran quantum simulation and QUBO solving,
   persisted project memory, created an unapproved handoff, denied network
   research under `LOCAL_ONLY`, and resumed an approval-gated paper workflow
   after reconstructing the service from persisted state.

## Release gates

The following checks passed on the current development line:

```bash
python -m pytest -q
atelier acceptance
atelier acceptance --clean
atelier route-eval
atelier reliability --suite v2 --repetitions 2
atelier package check
atelier state validate --home ~/Atelier
atelier performance
```

Observed results:

- full Python suite: passed;
- capability routing: 16/16 cases, including `LOCAL_ONLY` abstention;
- reliability v2: 22/22 trials, no classified failures;
- package syntax/readiness: valid;
- active external runtime: valid, 223 verified chunks across three papers;
- service performance baseline: all operations passed;
- master protection: required `Python 3.11` status check, strict checks, no
  force-pushes, and no deletions.

## Deliberate release limits

This release remains local-first. It does not claim provider-backed quantum
execution, external solver availability, kernel-level sandboxing, automatic
cloud routing, or a signed artifact. Network research and frontier handoffs
remain explicit, user-selected operations. These are documented extensions,
not hidden dependencies of the local workbench.
