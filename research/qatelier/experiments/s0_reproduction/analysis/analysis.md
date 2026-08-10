# S0 calibration analysis

This is a preregistered calibration report, not evidence of quantum advantage.

- Raw rows: 1440 / expected 1440
- Confirmation seeds: 5
- Provider contact: False
- Jobs submitted: 0

## Candidate summaries

| Type | Candidate | q | Exact accuracy mean ± std | Finite-shot accuracy mean ± std |
| --- | --- | ---: | ---: | ---: |
| classical | finite_rbf | 2 | 0.7603 ± 0.0845 | — |
| classical | finite_rbf | 4 | 0.7427 ± 0.0722 | — |
| classical | linear_svm | 2 | 0.7833 ± 0.0776 | — |
| classical | linear_svm | 4 | 0.8171 ± 0.0389 | — |
| classical | logistic | 2 | 0.7833 ± 0.0767 | — |
| classical | logistic | 4 | 0.8165 ± 0.0389 | — |
| classical | low_rank_bilinear | 2 | 0.5938 ± 0.1687 | — |
| classical | low_rank_bilinear | 4 | 0.6634 ± 0.1309 | — |
| classical | matched_mlp | 2 | 0.7648 ± 0.0728 | — |
| classical | matched_mlp | 4 | 0.8048 ± 0.0365 | — |
| classical | polynomial_svm | 2 | 0.5100 ± 0.0358 | — |
| classical | polynomial_svm | 4 | 0.5359 ± 0.0295 | — |
| classical | rbf_svm | 2 | 0.7622 ± 0.0957 | — |
| classical | rbf_svm | 4 | 0.8103 ± 0.0534 | — |
| classical | rff | 2 | 0.7496 ± 0.0838 | — |
| classical | rff | 4 | 0.6754 ± 0.0991 | — |
| quantum_simulator | QIA-L-q2-R1 | 2 | 0.4991 ± 0.0127 | 0.4996 ± 0.0138 |
| quantum_simulator | QIA-L-q2-R2 | 2 | 0.4440 ± 0.0702 | 0.4441 ± 0.0690 |
| quantum_simulator | QIA-L-q4-R1 | 4 | 0.5001 ± 0.0065 | 0.5000 ± 0.0061 |
| quantum_simulator | QIA-L-q4-R2 | 4 | 0.4486 ± 0.0667 | 0.4483 ± 0.0664 |
| quantum_simulator | QIA-P-q2-R1 | 2 | 0.5004 ± 0.0108 | 0.5005 ± 0.0102 |
| quantum_simulator | QIA-P-q2-R2 | 2 | 0.4576 ± 0.0639 | 0.4578 ± 0.0643 |
| quantum_simulator | QIA-P-q4-R1 | 4 | 0.4991 ± 0.0090 | 0.4991 ± 0.0101 |
| quantum_simulator | QIA-P-q4-R2 | 4 | 0.4654 ± 0.0576 | 0.4642 ± 0.0582 |

Paired deltas are against the logistic baseline on the same training selection, confirmation seed, and compressed representation. Bootstrap intervals are descriptive calibration intervals; they do not establish a C1/C2 claim.
