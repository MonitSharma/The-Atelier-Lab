# QAtelier current-phase audit

Status: negative result audited; no quantum advantage or hardware utility claim is supported.

The S0 calibration, S1 classical reference panels, fair-projection S2 mechanism screen, and no-candidate freeze are hash-linked. Read-only provider discovery was performed, but every archived scientific execution manifest records zero provider jobs. Quantinuum physical jobs: 0.

Frozen candidates: none.
Hardware authorized: false.
C1–C4 claim supported: false.

Reproduction commands:

```bash
.venv/bin/pytest -q research/qatelier/tests
.venv/bin/python scripts/validate_experiments.py
```
