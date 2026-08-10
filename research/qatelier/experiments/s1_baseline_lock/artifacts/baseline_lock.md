# S1 classical baseline lock

Status: SST-2 reference locked; full multi-task S1 remains incomplete.

This artifact is derived from the completed S0 raw bundle. It performs no retraining, confirmation-seed selection, or test tuning.

| Group | Candidate | q | Mean accuracy | Sample std | n |
| --- | --- | ---: | ---: | ---: | ---: |
| parameter_matched | finite_rbf | 2 | 0.7603 | 0.0845 | 60 |
| parameter_matched | finite_rbf | 4 | 0.7427 | 0.0722 | 60 |
| parameter_matched | linear_svm | 2 | 0.7833 | 0.0776 | 60 |
| parameter_matched | linear_svm | 4 | 0.8171 | 0.0389 | 60 |
| parameter_matched | logistic | 2 | 0.7833 | 0.0767 | 60 |
| parameter_matched | logistic | 4 | 0.8165 | 0.0389 | 60 |
| parameter_matched | low_rank_bilinear | 2 | 0.5938 | 0.1687 | 60 |
| parameter_matched | low_rank_bilinear | 4 | 0.6634 | 0.1309 | 60 |
| parameter_matched | matched_mlp | 2 | 0.7648 | 0.0728 | 60 |
| parameter_matched | matched_mlp | 4 | 0.8048 | 0.0365 | 60 |
| strong_reference | polynomial_svm | 2 | 0.5100 | 0.0358 | 60 |
| strong_reference | polynomial_svm | 4 | 0.5359 | 0.0295 | 60 |
| strong_reference | rbf_svm | 2 | 0.7622 | 0.0957 | 60 |
| strong_reference | rbf_svm | 4 | 0.8103 | 0.0534 | 60 |
| parameter_matched | rff | 2 | 0.7496 | 0.0838 | 60 |
| parameter_matched | rff | 4 | 0.6754 | 0.0991 | 60 |

Unresolved S1 tasks: semantic_pair, additional_classification, scientific_retrieval, controlled_interaction_order.
