# Current results

This is the canonical short summary of measured results. Numbers below are grounded in committed reports and remain bounded by their small suites.

## Local systems

The local inference experiment reports Q4_K_M decode rates of 39.3 tok/s for qwen3:4b, 11.5 tok/s for qwen3:14b, and 27.9 tok/s for gemma4:26b on an M3 Pro 36 GB machine. The result is a reminder that parameter count alone does not predict decode speed; architecture and kernel shape matter. See [experiment 003](../foundation/experiments/003_local_inference_benchmark/README.md).

## Agent reliability

The latest expanded reports record 17/18 knowledge answers correct, 13/13 code tasks solved, and 10/10 combined tasks solved. These are frozen, modest, mostly single-file suites; they do not establish repository-scale reliability.

The initial three-task baseline recorded 2/3 code tasks solved and suggested a structural-edit reasoning limit. Subsequent diagnosis found that a workspace path-handoff defect and edit-normalization issue materially contributed to the failure. After correcting those defects, the expanded 13-task suite passed. This does not establish general repository-scale coding reliability because the suite remains small and primarily single-file.

The router result is 43.8% base accuracy versus 100% after a 0.5B LoRA fine-tune on an in-distribution held-out set. Treat the lift as a component result, not a generalization guarantee.

## Foundation

The committed nanochat baseline reports approximately 18,700 tok/s for 73.5M parameters and 4,470 tok/s for 286.2M parameters, with validation BPB 1.1664 and 1.0954 respectively at 5,000 steps. These are historical runs, not results from the educational `minillm` implementation.
