# 02 — Bigram language model

**Concept.** A bigram predicts the next token from only the current token using an embedding/table of logits. **Background.** Conditional probability and negative log-likelihood. **Shapes.** Input and target `(batch, time)`, logits `(batch, time, vocab)`.

**Task.** Train `BigramLanguageModel` on the tiny fixture and sample text. **Verify.** A fixed seed gives finite loss and training loss falls. **Mistakes.** Leaking the next token, mixing up vocabulary dimensions, and evaluating on training data only.

**Production connection.** This is the simplest version of `minillm`'s language-model head. **Read.** A small autoregressive language-model chapter. **Exit.** Implement the target shift and explain why sampling uses the final time step.
