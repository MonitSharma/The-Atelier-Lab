# S1 classical baseline lock

Status: SST-2, MRPC, and CoLA reference tables locked; retrieval and controlled-order conditions remain open.

All rows use frozen train-only representations, fixed confirmation seeds, and no test tuning.

| Task | Group | Candidate | q | Mean accuracy | Sample std | n |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| sst2 | parameter_matched | finite_rbf | 2 | 0.7603 | 0.0845 | 60 |
| sst2 | parameter_matched | finite_rbf | 4 | 0.7427 | 0.0722 | 60 |
| sst2 | parameter_matched | linear_svm | 2 | 0.7833 | 0.0776 | 60 |
| sst2 | parameter_matched | linear_svm | 4 | 0.8171 | 0.0389 | 60 |
| sst2 | parameter_matched | logistic | 2 | 0.7833 | 0.0767 | 60 |
| sst2 | parameter_matched | logistic | 4 | 0.8165 | 0.0389 | 60 |
| sst2 | parameter_matched | low_rank_bilinear | 2 | 0.5938 | 0.1687 | 60 |
| sst2 | parameter_matched | low_rank_bilinear | 4 | 0.6634 | 0.1309 | 60 |
| sst2 | parameter_matched | matched_mlp | 2 | 0.7648 | 0.0728 | 60 |
| sst2 | parameter_matched | matched_mlp | 4 | 0.8048 | 0.0365 | 60 |
| sst2 | strong_reference | polynomial_svm | 2 | 0.5100 | 0.0358 | 60 |
| sst2 | strong_reference | polynomial_svm | 4 | 0.5359 | 0.0295 | 60 |
| sst2 | strong_reference | rbf_svm | 2 | 0.7622 | 0.0957 | 60 |
| sst2 | strong_reference | rbf_svm | 4 | 0.8103 | 0.0534 | 60 |
| sst2 | parameter_matched | rff | 2 | 0.7496 | 0.0838 | 60 |
| sst2 | parameter_matched | rff | 4 | 0.6754 | 0.0991 | 60 |
| mrpc | parameter_matched | finite_rbf | 4 | 0.6027 | 0.0572 | 60 |
| mrpc | parameter_matched | linear_svm | 4 | 0.6318 | 0.0564 | 60 |
| mrpc | parameter_matched | logistic | 4 | 0.6284 | 0.0576 | 60 |
| mrpc | parameter_matched | low_rank_bilinear | 4 | 0.5505 | 0.0771 | 60 |
| mrpc | parameter_matched | matched_mlp | 4 | 0.6253 | 0.0533 | 60 |
| mrpc | strong_reference | polynomial_svm | 4 | 0.5225 | 0.0297 | 60 |
| mrpc | strong_reference | rbf_svm | 4 | 0.6143 | 0.0615 | 60 |
| mrpc | parameter_matched | rff | 4 | 0.5582 | 0.0591 | 60 |
| cola | parameter_matched | finite_rbf | 4 | 0.5090 | 0.0399 | 60 |
| cola | parameter_matched | linear_svm | 4 | 0.5246 | 0.0567 | 60 |
| cola | parameter_matched | logistic | 4 | 0.5242 | 0.0573 | 60 |
| cola | parameter_matched | low_rank_bilinear | 4 | 0.4904 | 0.0515 | 60 |
| cola | parameter_matched | matched_mlp | 4 | 0.5211 | 0.0649 | 60 |
| cola | strong_reference | polynomial_svm | 4 | 0.4949 | 0.0305 | 60 |
| cola | strong_reference | rbf_svm | 4 | 0.5159 | 0.0476 | 60 |
| cola | parameter_matched | rff | 4 | 0.5133 | 0.0471 | 60 |

Unresolved S1 tasks: controlled_interaction_order.
