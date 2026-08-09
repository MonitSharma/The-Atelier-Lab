# Learning path

Work in dependency order. Each stage should leave a small executable artifact and a test result.

| Stage | Concepts | Artifact | Exit criterion |
|---|---|---|---|
| 00 | tensors, logits, softmax, loss | hand-computed loss check | explain every shape and value |
| 01 | characters, bytes, BPE | encode/decode and fertility report | compare Sanskrit and English token costs |
| 02 | conditional likelihood | tiny bigram model | overfit a toy corpus and sample from it |
| 03 | Q/K/V and masking | causal attention | prove future tokens are invisible |
| 04 | transformer blocks | tiny language model | trace one batch through the block |
| 05 | optimization and checkpoints | reproducible trainer | resume and match a saved step |
| 06 | prefill, decode, KV cache | generation benchmark | report TTFT and decode rate |
| 07 | quantization and memory | memory worksheet | estimate weights plus KV cache |
| 08 | ReAct, tools, retrieval, verification | agent reliability note | connect every claim to an Atelier component |

Use [RESEARCH_METHOD.md](RESEARCH_METHOD.md) for experiments and [GLOSSARY.md](GLOSSARY.md) when a term is unfamiliar. Do not use rigid dates; advance when the exit criterion is met.
