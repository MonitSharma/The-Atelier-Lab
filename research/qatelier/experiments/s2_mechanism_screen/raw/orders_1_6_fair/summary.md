# S2 orders 1–6 fair-projection panel

This is a diagnostic bundle, not a candidate freeze or an advantage claim. The q=2/4 panel covers all four QIA families, orders 1–6, two re-upload counts, and three classical controls. For each q, classical and quantum rows consume the identical first-q feature projection; the train and evaluation matrix hashes are recorded in every row.

| Model type | Candidate | Mean accuracy | Sample std | n |
| --- | --- | ---: | ---: | ---: |
| classical | logistic-q2 | 0.5495 | 0.1156 | 24 |
| classical | logistic-q4 | 0.5508 | 0.1258 | 24 |
| classical | matched_mlp-q2 | 0.5439 | 0.1286 | 24 |
| classical | matched_mlp-q4 | 0.5378 | 0.1119 | 24 |
| classical | rbf_svm-q2 | 0.5791 | 0.1218 | 24 |
| classical | rbf_svm-q4 | 0.5557 | 0.1080 | 24 |
| quantum_simulator | QIA-A/L/P/X-q2-R1 | 0.4984 | 0.0406 | 24 each |
| quantum_simulator | QIA-A/L/P/X-q2-R2 | 0.4974 | 0.0417 | 24 each |
| quantum_simulator | QIA-A/L/P/X-q4-R1 | 0.4984 | 0.0406 | 24 each |
| quantum_simulator | QIA-A/L/P/X-q4-R2 | 0.4974 | 0.0417 | 24 each |

Aggregate classical accuracy across the 144 matched rows: 0.5528. Provider contacted: false. Jobs submitted: 0. Candidate freeze: false.
