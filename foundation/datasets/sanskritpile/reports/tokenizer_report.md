# Tokenizer Efficiency and Vocabulary Report

This document reports the comparative statistics and vocabulary details of custom BPE tokenizers (vocab = 32,768) trained on matched splits.

## BPE Optimization Table

| Corpus | Raw Bytes | Unicode Chars | Lines | Vocab | Tokens | Bytes/token | Chars/token | Unique Token Ratio |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **English-Byte** | 52,200,179 | 51,975,022 | 228,622 | 32,768 | 11,227,580 | 4.6493 | 4.6292 | 0.0031 |
| **Sanskrit** | 52,346,620 | 19,256,827 | 82,178 | 32,768 | 8,972,554 | 5.8341 | 2.1462 | 0.0038 |
| **English-Char** | 19,249,879 | 19,182,342 | 89,127 | 32,768 | 4,126,314 | 4.6652 | 4.6488 | 0.0083 |

## Vocabulary Utilization & Sparsity Checks

Because the dataset sizes are relatively small (19.3MB–50MB), some BPE vocabulary entries may remain sparse or completely unused.

| Metric | English-Byte | Sanskrit | English-Char |
| :--- | :--- | :--- | :--- |
| **Vocab Utilization (%)** | 99.31% | 98.78% | 98.73% |
| **Tokens with Frequency = 1** | 121 | 177 | 353 |
| **Top 1% Token Mass** | 1 tokens | 1 tokens | 1 tokens |
| **Top 10% Token Mass** | 3 tokens | 4 tokens | 3 tokens |
| **Top 50% Token Mass** | 265 tokens | 56 tokens | 266 tokens |
