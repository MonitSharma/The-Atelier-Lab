# S1 — classical baseline lock

S1 freezes the classical reference numbers before any QAtelier mechanism
screening. The current artifact locks the SST-2 condition from the completed
S0 raw bundle and does not claim that the multi-task S1 stage is complete.

The locked groups are:

- strong references: RBF SVM and polynomial SVM;
- parameter-matched controls: logistic, linear SVM, RFF, matched MLP,
  low-rank bilinear, and finite RBF.

The scientific retrieval and controlled interaction-order tasks remain explicit
prerequisites for advancing S1 to a full baseline lock. SST-2, MRPC, and CoLA
now have archived classical reference panels.

The MRPC semantic-pair manifest and deterministic split manifest are now
committed. A local preparation validation produced 1,522 selected pairs as
3,072-dimensional `[e1; e2; abs(e1-e2); e1*e2]` features and 12 train-only
compressors; the validation record is
[`mrpc_preparation_validation.json`](mrpc_preparation_validation.json).

CoLA is also pinned as the additional classification condition. Its prepared
validation produced 1,795 selected sentences, 768-dimensional embeddings, and
12 train-only compressors; see
[`cola_preparation_validation.json`](cola_preparation_validation.json).

The archived MRPC and CoLA head panels are in `raw/mrpc/` and `raw/cola/`.
Each has 480 rows: 3 training selections × 4 budgets × 5 confirmation seeds
× 8 heads. They are classical-only and record zero provider jobs. The
multi-task reference lock is [`artifacts/baseline_lock_all.json`](artifacts/baseline_lock_all.json)
with a readable table in
[`artifacts/baseline_lock_all.md`](artifacts/baseline_lock_all.md).

Prepare the pair cache with the same pinned MPNet snapshot used by S0:

```bash
python -m research.qatelier.experiments.s1_baseline_lock.prepare_pair_data \
  --config research/qatelier/experiments/s1_baseline_lock/config.yaml \
  --train /path/to/train.parquet \
  --validation /path/to/validation.parquet \
  --encoder-path /path/to/pinned/paraphrase-mpnet-base-v2 \
  --output-dir /path/to/new/mrpc-prepared
```

To rebuild the committed multi-task table after reproducing the two raw
panels:

```bash
python -m research.qatelier.experiments.s1_baseline_lock.lock_all \
  --config research/qatelier/experiments/s1_baseline_lock/config.yaml \
  --output-dir /path/to/new/s1-lock-all
```

Run against the committed S0 raw bundle:

```bash
python -m research.qatelier.experiments.s1_baseline_lock.lock \
  --config research/qatelier/experiments/s1_baseline_lock/config.yaml \
  --output-dir /path/to/new/s1-lock
```
