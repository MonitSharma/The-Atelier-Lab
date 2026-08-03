# 00 — Tensors and probability

**Concept.** Tensors hold batches, positions, vocabularies, and features. Logits become probabilities with softmax; log probabilities make products additive; cross-entropy is negative log probability of the observed next token.

**Background.** Matrix multiplication, exponentials, logarithms, and basic probability. **Shapes.** Logits `(batch, time, vocab)`, targets `(batch, time)`, loss scalar.

**Task.** Hand-compute one next-token loss from three logits and compare it with PyTorch. **Verify.** Assert agreement within `1e-6` in a CPU test. **Mistakes.** Applying softmax before `cross_entropy`, using the wrong target shift, and averaging over padding.

**Production connection.** `foundation/minillm/model.py` returns the same logits shape used by `atelier_agent` models. **Read.** The cross-entropy section of a standard deep-learning text. **Exit.** Explain the target shift and calculate one loss without a library.
