# 07 — Quantization and memory

**Concept.** Weight memory is roughly parameters × bytes per weight; KV memory grows with context, layers, heads, and head dimension. FP32/FP16/BF16/INT8/INT4 trade precision, memory, and speed. **Background.** Powers of two and dimensional analysis.

**Task.** Estimate weights plus KV cache for a hypothetical model under 36 GB. **Verify.** Compare with the committed benchmark's resident-memory column. **Mistakes.** Counting only weights, treating bit width as bytes, and assuming parameter count predicts speed.

**Production connection.** Model roles and quantization are configured in `atelier_agent/atelier/config.py`. **Read.** A quantization survey. **Exit.** State what a memory budget can and cannot predict.
