# S1 — classical baseline lock

S1 freezes the classical reference numbers before any QAtelier mechanism
screening. The current artifact locks the SST-2 condition from the completed
S0 raw bundle and does not claim that the multi-task S1 stage is complete.

The locked groups are:

- strong references: RBF SVM and polynomial SVM;
- parameter-matched controls: logistic, linear SVM, RFF, matched MLP,
  low-rank bilinear, and finite RBF.

The semantic-pair, additional classification, scientific retrieval, and
controlled interaction-order tasks remain explicit prerequisites for advancing
S1 to a full baseline lock.

Run against the committed S0 raw bundle:

```bash
python -m research.qatelier.experiments.s1_baseline_lock.lock \
  --config research/qatelier/experiments/s1_baseline_lock/config.yaml \
  --output-dir /path/to/new/s1-lock
```
