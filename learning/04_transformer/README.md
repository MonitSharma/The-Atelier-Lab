# 04 — Transformer

**Concept.** Embeddings, position information, attention, feed-forward layers, residuals, normalization, and an LM head form a transformer. Weight tying reuses input embeddings at the output. **Background.** Attention and optimization. **Shapes.** Hidden state `(batch, time, dim)`, vocabulary logits `(batch, time, vocab)`.

**Task.** Trace one fixture batch through `TransformerLM`. **Verify.** CPU forward pass has the documented shape and finite loss. **Mistakes.** Residual shape mismatches and unmasked causal attention.

**Production connection.** This is the educational counterpart to the local models used by Atelier. **Read.** Transformer architecture notes. **Exit.** Explain why residuals make depth trainable.
