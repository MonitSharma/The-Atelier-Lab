# Duplicates Report

This report documents the multi-level deduplication statistics.

## Deduplication Metrics Table

| Stage | Scanned | Removed | Duplicate Rate (%) |
| :--- | ---: | ---: | ---: |
| **Document-level (Exact)** | 48,130 | 168 | 0.35% |
| **Paragraph-level (Global Boilerplate)** | - | 0 | - |
| **Line-level (Local Cyclic)** | 51,821 | 22 | 0.04% |

## Scientific Verification
*   **Success Criterion (Duplicate Line Rate < 2%)**: **SUCCESS** (Final line duplication rate: **0.0425%**).
