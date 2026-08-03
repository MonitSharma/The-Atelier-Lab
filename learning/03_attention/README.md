# 03 — Attention

**Concept.** Queries ask, keys match, and values carry information. Scaled dot-product attention weights values by query-key similarity; a causal mask blocks the future. **Background.** Matrix multiplication and softmax. **Shapes.** Q/K/V `(batch, heads, time, head_dim)`, scores `(batch, heads, time, time)`.

**Task.** Use `scaled_dot_product_attention` and then multi-head causal attention. **Verify.** Perturbing a future token cannot change an earlier output. **Mistakes.** Wrong transpose, missing `sqrt(head_dim)`, and masking after softmax.

**Production connection.** `foundation/minillm/attention.py` is the executable reference. **Read.** “Attention Is All You Need.” **Exit.** Draw the score tensor and explain every axis.
