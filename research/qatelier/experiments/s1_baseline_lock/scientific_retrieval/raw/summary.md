# SciFact classical retrieval reference panel

The panel contains 360 rows: 9 train-only representations × 5 confirmation seeds × 8 heads. Reserved test qrels were not used. Metrics are averaged over the 64 confirmation queries per row.

| Candidate | Metric | Mean | Sample std | n |
| --- | --- | ---: | ---: | ---: |
| finite_rbf | mrr_at_10 | 0.0021 | 0.0035 | 45 |
| finite_rbf | ndcg_at_10 | 0.0033 | 0.0047 | 45 |
| finite_rbf | recall_at_10 | 0.0075 | 0.0100 | 45 |
| linear_svm | mrr_at_10 | 0.0225 | 0.0185 | 45 |
| linear_svm | ndcg_at_10 | 0.0321 | 0.0221 | 45 |
| linear_svm | recall_at_10 | 0.0666 | 0.0393 | 45 |
| logistic | mrr_at_10 | 0.0261 | 0.0177 | 45 |
| logistic | ndcg_at_10 | 0.0365 | 0.0209 | 45 |
| logistic | recall_at_10 | 0.0727 | 0.0370 | 45 |
| low_rank_bilinear | mrr_at_10 | 0.0045 | 0.0055 | 45 |
| low_rank_bilinear | ndcg_at_10 | 0.0060 | 0.0062 | 45 |
| low_rank_bilinear | recall_at_10 | 0.0114 | 0.0112 | 45 |
| matched_mlp | mrr_at_10 | 0.0160 | 0.0184 | 45 |
| matched_mlp | ndcg_at_10 | 0.0205 | 0.0212 | 45 |
| matched_mlp | recall_at_10 | 0.0369 | 0.0330 | 45 |
| polynomial_svm | mrr_at_10 | 0.0159 | 0.0144 | 45 |
| polynomial_svm | ndcg_at_10 | 0.0215 | 0.0171 | 45 |
| polynomial_svm | recall_at_10 | 0.0416 | 0.0292 | 45 |
| rbf_svm | mrr_at_10 | 0.0240 | 0.0179 | 45 |
| rbf_svm | ndcg_at_10 | 0.0354 | 0.0232 | 45 |
| rbf_svm | recall_at_10 | 0.0750 | 0.0456 | 45 |
| rff | mrr_at_10 | 0.0006 | 0.0026 | 45 |
| rff | ndcg_at_10 | 0.0007 | 0.0028 | 45 |
| rff | recall_at_10 | 0.0012 | 0.0040 | 45 |

Provider contacted: false. Jobs submitted: 0. Test qrels used: false.
