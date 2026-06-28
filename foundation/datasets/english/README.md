# English Matched Baseline Corpora

This directory describes the matched English corpora prepared to control for pretraining benchmarks.

## 1. English-Byte Corpus (Byte-Matched Control)
*   **Target**: Match the storage/byte footprint of the Sanskrit corpus (50 MB).
*   **Size**: Exactly **52,428,800 bytes** (52.2M characters).
*   **Source**: `HuggingFaceFW/fineweb-edu` (config `sample-10BT`).
*   **Tokens (after BPE)**: 11,227,580 tokens.
*   **Zipfian Concentration**: **265 tokens** represent **50% of the token mass** in the corpus.

---

## 2. English-Char Corpus (Character-Matched Control)
*   **Target**: Match the Unicode character count of the Sanskrit corpus (19,339,005 characters).
*   **Size**: Exactly **19,339,005 bytes** (19.3M characters, since English ASCII uses 1 byte per character).
*   **Source**: Truncated subset of the same `HuggingFaceFW/fineweb-edu` stream.
*   **Tokens (after BPE)**: 4,126,314 tokens.
*   **Zipfian Concentration**: **266 tokens** represent **50% of the token mass** in the corpus.
