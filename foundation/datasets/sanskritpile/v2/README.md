# Sanskrit Pile - Version 2 (V2) (Planned)

Sanskrit Pile V2 is planned to address the Zipfian repeat-pattern confounders observed in V1, targeting a cleaner, modern Sanskrit prose corpus.

## Target Methodology

### 1. Bilingual Parallel Corpora Curation
To extract clean modern prose, we will ingest bilingual parallel Sanskrit-Hindi datasets:
*   **SAHAAYAK 2023**: Contains ~1.5M parallel Sanskrit-Hindi pairs spanning multiple domains.
*   **Samasāmayik 2026**: Contains ~92,196 parallel pairs specifically focused on contemporary news, essays, and modern prose.

### 2. De-duplication & Cleaning Pipeline
*   Implement strict document-level MinHash LSH de-duplication to bring down the duplicate line rate from **19.69%** to **< 2%**.
*   Strip structural boilerplate headers (e.g. repeated Swami Vivekananda comment indices, editor copyright strings).

### 3. Shared Tokenizer Control
To isolate the "language vs. tokenizer" effects:
*   Train a **shared multilingual byte-level / shared BPE tokenizer** on matched Hindi/Sanskrit/English corpora.
*   Compare models trained using custom tokenizers (adaptation testing) vs. a shared tokenizer (pure language-structure testing).
