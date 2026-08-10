# QAtelier requirements audit

This table audits the governing execution plan against the current `qatelier`
branch. “Not run” entries are intentional only where the preceding gate
failed or the plan forbids execution.

| Requirement | Status | Evidence / limitation |
| --- | --- | --- |
| Work isolated on `qatelier` | Complete | `git branch --show-current`; current branch is `qatelier`. |
| QAtelier infrastructure and schema validation | Complete | `config.yaml`, `schemas/`, CLI, explicit tests, CI QAtelier step. |
| Frozen public MPNet representation | Complete | S0 encoder/data/preparation manifests and hashes. |
| Train-only compression | Complete | S0/S1 compressor artifacts and preparation validators. |
| Strong classical references | Complete | RBF and polynomial SVM panels in S0/S1 raw bundles. |
| Parameter-matched classical controls | Complete | Logistic, linear SVM, RFF, MLP, bilinear, finite RBF panels. |
| S0 calibration | Complete | 1,440-row raw bundle, exact/finite-shot analysis, negative result. |
| MRPC and CoLA public tasks | Complete | Manifests, preparation validation, 480-row panels each. |
| SciFact retrieval | Complete for current phase | Pinned source/qrels, external 768-D preparation evidence, 360-row panel; reserved test qrels unused. |
| Controlled order 1–6 benchmark | Complete for current phase | 24 frozen problems, 192 split records, 14,400-row classical panel. |
| S2 QIA-P/L/X/A mechanism screen | Complete as bounded fair-projection screen | Authoritative 528-row q=2/4 all-order panel under `raw/orders_1_6_fair/`; classical and quantum rows share the same first-q matrix hashes. The earlier unequal-information 456-row panel is retained as rejected audit evidence. q=6 was not completed because the finite-difference simulator was impractical. |
| Candidate freeze | Complete | `analysis/candidate_freeze.json`; frozen candidates empty. |
| OOD protocol | Locked, not executed | `experiments/s3_heldout/`; no candidate existed for a valid quantum comparison. |
| S4 noise campaign | Not authorized | Candidate freeze failed; no noise result is implied. |
| IBM physical validation | Not executed by design | Read-only preflight only; no frozen candidate. |
| Quantinuum Helios-1E | Not executed by design | Exact identifier verified; no frozen candidate and no cost campaign. |
| Quantinuum physical QPU | Forbidden in this phase | Code/configuration lock; physical jobs are zero. |
| HQC cost manifests | Ready, no campaign artifact | Cost guard requires exact accepted manifest before any future emulator submission. |
| Statistics and uncertainty | Partial but explicit | S0 bootstrap intervals and S1/S2 descriptive means/std are archived; clustered paired inference, final held-out quantum effect sizes, and multiple-testing correction remain future-study requirements. |
| Final claim discipline | Complete | Current claim is C0; no C1–C4 claim. |
| Final report/manuscript draft | Complete for current phase | `FINAL_RESEARCH_REPORT.md`, `manuscript/`, hardware decisions, audit package. |

The current phase therefore ends at a reproducible negative simulator result.
Any future positive claim requires a new approved preregistration that cannot
reuse confirmation/OOD results for selection and must pass the same hardware
gates.
