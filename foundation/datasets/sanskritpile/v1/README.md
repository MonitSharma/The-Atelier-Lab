# Sanskrit Pile - Version 1 (V1)

Sanskrit Pile V1 is a **50 MB (52,428,800 bytes)** corpus curated to establish a baseline pretraining run on local hardware.

## Dataset Specifications
*   **Total Bytes**: 52,346,620
*   **Unicode Characters**: 19,256,827
*   **Total BPE Tokens**: 8,972,554
*   **Characters per Token**: 2.15
*   **Bytes per Token**: 5.83

## Data Provenance
*   **Sources**:
    *   `Henil1/sanskrit` (Hugging Face): General prose and translations.
    *   `saucam/sans_data` (Hugging Face): Wikipedia dumps and general prose.
*   **Curation Rules**:
    *   Kept only Devanagari Unicode characters (`\u0900` to `\u097F`).
    *   Removed HTML tags and URLs.
    *   Excluded lines containing Latin letters to filter out English headers and transliterated (IAST) texts.

## Known Quality Issues (Confounders)
*   **Duplicate Line Rate**: **19.69%**
*   **Zipfian Concentration**: A tiny subset of **56 tokens** represents **50% of the entire token mass** in the corpus. This high concentration is driven by standard recurring sloka headers and template strings in the classical texts database, which makes the text artificially predictable to the loss function.
