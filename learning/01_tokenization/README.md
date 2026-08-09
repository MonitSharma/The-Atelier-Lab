# 01 — Tokenization

**Concept.** Characters, bytes, and subwords trade vocabulary size against sequence length. BPE learns merges. **Background.** Strings, Unicode, counting. **Shapes.** Token IDs `(time,)` or `(batch, time)`.

**Task.** Encode/decode English and Sanskrit with `minillm` character and byte tokenizers; report bytes per token and fertility. **Verify.** Round trips must equal the original text. **Mistakes.** Treating Unicode characters as bytes, losing unknown symbols, and measuring only vocabulary size.

**Production connection.** Compare the existing Sanskrit/English pilot under `foundation/experiments/002_sanskrit_vs_english_pilot/`. **Read.** The original BPE paper or tokenizer chapter. **Exit.** Describe why tokenization changes both memory and learning signal.
