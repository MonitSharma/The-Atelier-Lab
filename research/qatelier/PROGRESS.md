# QAtelier progress

> Status: infrastructure hardening in progress. No scientific experiment result
> or production Atelier change is claimed here.

## Initial branch status

Snapshot taken on 2026-08-10 when the `qatelier` branch was created:

- branch: `qatelier`;
- `HEAD`: `efbe281` (`Add multimodal document evidence pipeline`);
- branch tip also matched the repository's `master` / `origin/master` at the
  snapshot;
- existing tracked QAtelier evaluation files were preserved:
  [`README.md`](README.md), [`initial_results.md`](initial_results.md), and
  [`questions.json`](questions.json);
- the existing document-evaluation workflow was preserved;
- the initial implementation work in this checkpoint is isolated under
  `research/qatelier/`; production code remains unchanged;
- the planned experiment is registered in
  [`experiments/registry.yaml`](../../experiments/registry.yaml).

## Work completed in this checkpoint

- [`ARCHITECTURE.md`](ARCHITECTURE.md) records the frozen-embedding → shared
  compression → classical/quantum-head design, claim ceiling, controls, and
  scope boundaries.
- `config.yaml` and the JSON schemas define the experiment metadata and result
  contract without requiring cloud credentials.
- `benchmark.py` provides deterministic synthetic interaction-order data, and
  `baselines.py` provides the matched classical-control catalogue.
- `manifest.py` provides stable experiment identity hashes and result envelopes.
- `quantum_adapter.py` defines the backend-neutral circuit/resource contract.
- Focused QAtelier tests pass: 15 tests plus 5 benchmark subtests.
- Repository checks pass: 7 experiments registered and validated.
- This file records the staged plan, gates, and reproducibility rules.
- The existing evaluation harness remains the source of truth for document
  ingestion and QAtelier question scoring; see the existing README and
  [`initial_results.md`](initial_results.md).
- The provider-access checkpoint is recorded in
  [`HARDWARE_ACCESS.md`](HARDWARE_ACCESS.md): IBM authentication succeeded;
  Quantinuum authentication and project access succeeded; no jobs were
  submitted; and hardware HQC authorization remains unverified.

## P0 infrastructure checkpoint — 2026-08-10

The following credential-free infrastructure is now implemented on `qatelier`:

- explicit CLI/config/schema validation in [`cli.py`](cli.py),
  [`config.py`](config.py), and `schemas/config.schema.json`; unresolved
  scientific locks refuse execution;
- deterministic toy smoke output from raw synthetic data to JSON, exposed by
  `make qatelier-smoke`;
- an executable NumPy PQC simulator with exact and finite-shot paths, QIA-P/L/X/A
  schedules, parameter-order serialization, disjoint two-qubit rounds, and
  optional Qiskit Aer cross-validation under [`simulation/`](simulation/);
- a reusable latent interaction benchmark whose target function and threshold
  are fixed once per problem and reused across independent splits;
- executable representation-matched classical controls under
  [`classical/`](classical/) for linear, SVM, random-feature, MLP, bilinear,
  finite-RBF, and spectrum-matched families; MPS remains an explicit unavailable
  optional backend rather than a fabricated result;
- read-only IBM preflight/frozen-panel gates and a Quantinuum policy that allows
  only the exact `Helios-1E` emulator, requires an accepted exact-match cost
  manifest, and rejects all physical Quantinuum execution;
- a 26-source literature/novelty audit under [`literature/`](literature/);
- train-only PCA/whitening artifacts, frozen encoder identity manifests, and
  pair-representation construction under [`data/`](data/);
- explicit QAtelier test and credential-free smoke steps in CI.
- an S0 preregistration under
  [`experiments/s0_reproduction/`](experiments/s0_reproduction/); its runner
  fails closed until the exact encoder, dataset, split, embedding, and
  compressor locks are committed;
- exact SST-2 archive/member hashes, deterministic stratified selections, and
  the pinned MPNet revision/weights digest are now committed in the S0
  manifests;
- the credential-free S0 preparation path in `run.py --prepare` validates those
  locks, encodes the declared union, and writes external immutable embedding
  and train-only PCA artifacts. A local validation run produced 1,902 examples,
  768-dimensional embeddings, and 12 compressor artifacts; its preparation
  record is [`preparation_validation.json`](experiments/s0_reproduction/preparation_validation.json).
- the S0 execution path now trains the declared classical controls and a
  finite-difference NumPy PQC panel, evaluates exact and fixed finite-shot
  expectations on all five confirmation seeds, and writes immutable raw JSON
  with parameter/resource/history hashes. A bounded smoke run produced 45 rows;
  its validation record is
  [`execution_validation.json`](experiments/s0_reproduction/execution_validation.json).
- the complete S0 panel is now archived under [`experiments/s0_reproduction/raw/`](experiments/s0_reproduction/raw/)
  with derived analysis under [`experiments/s0_reproduction/analysis/`](experiments/s0_reproduction/analysis/).
  It contains 1,440 rows across all 12 training selections, five confirmation
  seeds, eight simulator candidates, and the eight declared classical controls
  at q=2 and q=4. The completion manifest is
  [`s0_completion.json`](experiments/s0_reproduction/s0_completion.json).
- The calibration result is negative for the current short, preregistered
  optimization budget: quantum-head accuracy is near chance and below the
  classical controls in the archived analysis, while finite-shot metrics track
  exact simulation closely. This does not support a C1/C2 claim and is retained
  as a valid calibration outcome.
- S1 now contains a hash-linked SST-2 classical reference lock derived from
  those raw rows, separating strong references from parameter-matched controls.
  The lock is archived under
  [`experiments/s1_baseline_lock/artifacts/`](experiments/s1_baseline_lock/artifacts/).
- The first additional S1 public task is now pinned as MRPC: parquet member
  hashes, deterministic low-data/confirmation selections, and the pair
  representation preparation path are committed. A local validation produced
  1,522 selected pairs and 12 train-only compressors. Its full classical head
  panel is archived under `experiments/s1_baseline_lock/raw/mrpc/` with 480
  rows and zero provider jobs.
- CoLA is now pinned as the additional public classification condition, with
  deterministic splits and a validated frozen-embedding/compressor preparation
  path. Its full classical head panel is archived under
  `experiments/s1_baseline_lock/raw/cola/` with 480 rows and zero provider jobs.
  The combined SST-2/MRPC/CoLA reference table is
  [`experiments/s1_baseline_lock/artifacts/baseline_lock_all.json`](experiments/s1_baseline_lock/artifacts/baseline_lock_all.json),
  while the remaining scientific-retrieval and controlled-order definitions
  are now pinned for later head evaluation under
  `experiments/s1_baseline_lock/scientific_retrieval/` and
  `experiments/s1_baseline_lock/controlled_interaction_order/`. The controlled
  order definition also has a completed classical panel under its `raw/`
  directory: 14,400 rows across 24 problems, five budgets, five confirmation
  seeds, and eight heads, with zero provider jobs. Scientific-retrieval head
  evaluation remains pending because its corpus/embedding preparation is not
  vendored.
- The initial S2 mechanism screen is implemented with kernel alignment,
  effective-rank, spectrum, and finite-difference gradient diagnostics. A
  bounded screen over four interaction families and orders 1–4 is archived
  under [`experiments/s2_mechanism_screen/raw/`](experiments/s2_mechanism_screen/raw/);
  quantum heads were near chance and no candidate was frozen. This is a useful
  negative optimization/mechanism checkpoint, not a C1/C2 result.
- A bounded all-order S2 panel is now archived under
  `experiments/s2_mechanism_screen/raw/orders_1_6/`: 456 rows covering all
  four benchmark families, orders 1–6, q=2/4, all four QIA families, both
  re-upload counts, and three classical controls. It uses two short training
  steps, reports zero provider jobs, and explicitly freezes no candidate. A
  larger q=6 exploratory attempt was stopped after becoming impractical for
  the current finite-difference simulator; its declared configuration remains
  documented but no partial output was retained.

Focused QAtelier verification currently passes: 71 tests plus 7 benchmark
subtests, with Ruff clean. No provider job was submitted.

The repository-wide verification has two pre-existing/unrelated blockers in the
current local environment: excluding the known `pyarrow` build-test crash, 176
tests pass and three Atelier science-tool tests fail in QASM fallback/transpile
behavior; the full run then terminates with a native `pyarrow` segmentation fault
in `foundation/datasets/tests/test_build.py`. Those production failures are not
being silently changed in the QAtelier branch.

## Staged experiment plan

All stages are planned until their exit evidence is committed. A later stage
may not silently revise an earlier stage's split, baseline, or selection rule.

| Stage | Purpose | Required controls | Advance rule | Status |
| --- | --- | --- | --- | --- |
| S0 — reproduction/calibration | Reproduce a compact published-style frozen-embedding quantum-head setup and resolve discrepancies. | Same embeddings and splits for LR/SVM and the quantum head; record simulator and seed. | Basic behavior is reproduced or the discrepancy is explained. | Complete; negative calibration result archived |
| S1 — classical baseline lock | Establish the reference numbers before quantum screening. | Shared compressor, full nonlinear baseline ladder, equal validation/search budgets. | Search spaces, metrics, seeds, and reference outputs are frozen. | Partial multi-task lock: SST-2, MRPC, CoLA heads locked; controlled-order panel archived; retrieval head pending |
| S2 — mechanism screen | Test QIA-P/L/X/A across low-data and controlled interaction-order conditions. | Matched `q`, depth, trainable-parameter bands, optimization budget, and paired seeds; include aligned and deliberately misaligned tasks. | Retain only Pareto candidates with stable validation utility and non-pathological gradients. | Bounded orders 1–6 q=2/4 panel archived; candidate freeze pending |
| S3 — held-out simulator | Evaluate the frozen candidates on all predeclared public/OOD tasks. | No test tuning; report paired effect sizes and bootstrap intervals across seeds/tasks. | C1/C2 evidence exists, or a rigorous negative result explains the loss. | Planned |
| S4 — noise/shot screen | Estimate finite-shot and device-noise degradation. | Fixed shot budgets, noise-model versions, and candidate list; report gradient and resource costs. | Select 2–4 candidates only if signal is stable enough to justify QPU spend. | Planned |
| S5 — hardware pilot | Run a small, fixed sample slice on IBM and Quantinuum where access permits. | Frozen parameters, sample IDs, thresholds, shots, compilation settings, and one preregistered mitigation condition. | Outputs are stable enough for a main campaign; otherwise stop at simulation evidence. | Planned |
| S6 — main hardware | Validate the same selected models and declared ablations. | Logical-matched and hardware-co-designed comparisons; raw and fixed-mitigation results; provider records. | Claim only C3-level hardware utility when retention and ordering support it. | Planned |
| S7 — audit/package | Verify the complete result and claim trail. | Fresh-clone reproduction, seed audit, raw-data checks, resource audit, and claim-to-artifact map. | Every reported table/figure has a reproduction command and source artifact. | Planned |

### Kill and redirect rules

- If strong classical nonlinear heads remove the gain, stop the “quantum
  improvement” narrative and preserve the matched-baseline negative result.
- If product circuits match entangled circuits after resource matching, stop the
  entanglement-mechanism claim.
- If the hardware ordering is indistinguishable from shot/noise variability,
  do not claim hardware utility.
- If energy telemetry is unavailable, report QPU time and service/resource
  accounting only; do not infer an energy advantage.

## Reproducibility rules

1. Pin the encoder revision, tokenizer/pooling settings, dataset versions,
   licenses, split manifests, and hashes of cached embeddings.
2. Fit PCA/whitening or any compressor on the training split only. Save its
   fitted parameters and apply the identical transform to every head.
3. Use identical sample IDs, splits, labels, and seed lists across model
   families. Record the full training and validation histories, not only the
   winning seed.
4. Declare parameter-count bands, optimizer limits, epoch/early-stopping
   rules, and hyperparameter-search budgets before held-out evaluation.
5. Freeze architecture, parameters, samples, shots, thresholds, compilation,
   backend/noise-model versions, and mitigation settings before the first main
   hardware run. Hardware is validation, not a second search loop.
6. Record logical and compiled circuit resources: qubits, re-uploads, depth,
   trainable parameters, 1Q/2Q gates, routing/transport overhead, shots,
   circuit executions, QPU time, queue time separately, and provider job IDs.
7. Keep raw outputs immutable under the experiment's `raw/` directory; place
   derived plots under `figures/`; make analysis consume committed raw data.
8. Record hardware, software versions, backend/emulator metadata, configuration
   files, circuit/QASM or native representations, and the exact reproduction
   command.
9. Report paired effect sizes with uncertainty intervals. Do not promote a
   result from exploratory screening to a headline claim without the declared
   held-out analysis and claim-level artifact link.

## Immediate next actions

1. Prepare and lock the S1 scientific-retrieval classical reference heads; do
   not use confirmation results for quantum tuning. The controlled-order panel
   is already archived.
2. Add the remaining S2 ablations and paired-seed analysis, using the locked
   classical tables as the comparison reference; no candidate is frozen yet.
3. Keep IBM/Helios-1E execution gated until S2–S4 produce frozen candidates and
   accepted resource/cost manifests.

The optional provider dependencies and access checks are complete, but they do
not advance the staged experiment plan. Hardware remains gated behind the
simulator smoke test, frozen parameters, and explicit HQC authorization.

Until those actions are complete, QAtelier remains a planned parallel research
track and the production Atelier behavior remains unchanged.
