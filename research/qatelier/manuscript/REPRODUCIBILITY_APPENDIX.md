# Reproducibility appendix

## Frozen identifiers

- Encoder: `sentence-transformers/paraphrase-mpnet-base-v2`
- Revision: `6cc9279c672dc57f94445ef259b28a1b736fec8f`
- Weights SHA-256:
  `5fc2279bd6e503ca3543197b4ef00b615d87eebd02490f8c108aa3f35d7b705d`
- Quantinuum allowed emulator: `Helios-1E`
- Quantinuum physical execution: disabled

## Artifact map

| Evidence | Source |
| --- | --- |
| S0 raw and analysis | `experiments/s0_reproduction/raw/`, `analysis/` |
| S1 classical references | `experiments/s1_baseline_lock/` |
| S2 rejected unequal-input panel | `experiments/s2_mechanism_screen/raw/orders_1_6/` |
| S2 authoritative fair-projection panel | `experiments/s2_mechanism_screen/raw/orders_1_6_fair/` |
| S2 gate | `experiments/s2_mechanism_screen/analysis/candidate_freeze.json` |
| S3 OOD decision | `experiments/s3_heldout/decision.json` |
| Hardware ledger | `hardware/RUN_LEDGER.csv` |
| Current audit | `audit_artifacts/audit.json` |

## Commands

```bash
python3 -m pytest research/qatelier/tests -q
python3 -m ruff check research/qatelier
python3 scripts/validate_experiments.py
python3 -m research.qatelier.cli validate --json
```

No command in this appendix submits a provider job. The hardware access
checkpoint did perform read-only provider discovery; the scientific run
manifests record zero circuit jobs and zero shots.
