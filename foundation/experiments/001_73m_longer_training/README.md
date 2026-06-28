# Experiment 001: 73M Longer Training Run

The objective of this experiment is to determine whether the generation repetition issue observed in Experiment 000 is primarily a result of undertraining or if it is constrained by the parameter capacity of the 73M model.

## Objective
*   Train the **73M nanochat** model config for an extended period (**20,000 steps** instead of 5,000).
*   Monitor validation loss (BPB) convergence behavior.
*   Observe text generation sample progression over the training horizon to see when/if the repetition cycle breaks.

## Configuration Details
*   **Model**: 73M nanochat baseline configuration (depth=6, aspect-ratio=64, head-dim=64, n_embd=384, sequence_len=512).
*   **Total Training Tokens**: $20,000 \times 16,384 = 327,680,000$ tokens (~328 Million tokens).
*   **Validation Interval**: Every 100 steps (`--eval-every=100`).
*   **Sampling Interval**: Every 1,000 steps (`--sample-every=1000`).

## Execution Command
To run this experiment, execute the following command:

```bash
cd ~/code_projects/nanochat
source .venv/bin/activate

mkdir -p runs/local_logs

# Run the 20,000-step training wrapped in caffeinate to prevent sleep
caffeinate -i python -m scripts.base_train \
    --depth=6 \
    --head-dim=64 \
    --window-pattern=L \
    --max-seq-len=512 \
    --device-batch-size=32 \
    --total-batch-size=16384 \
    --eval-every=100 \
    --eval-tokens=524288 \
    --core-metric-every=-1 \
    --sample-every=1000 \
    --num-iterations=20000 \
    --model-tag="d6_longer_training" \
    --run=dummy 2>&1 | tee runs/local_logs/001_73m_longer_training_$(date +%Y%m%d_%H%M).log
```

## Expected Output
*   **Estimated Duration**: ~4.5 to 5 hours on MacBook Pro M3 Pro.
*   **Memory Footprint**: ~4 GB Unified Memory.
