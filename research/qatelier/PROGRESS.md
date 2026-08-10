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

Focused QAtelier verification currently passes: 66 tests plus 7 benchmark
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
| S0 — reproduction/calibration | Reproduce a compact published-style frozen-embedding quantum-head setup and resolve discrepancies. | Same embeddings and splits for LR/SVM and the quantum head; record simulator and seed. | Basic behavior is reproduced or the discrepancy is explained. | Planned |
| S1 — classical baseline lock | Establish the reference numbers before quantum screening. | Shared compressor, full nonlinear baseline ladder, equal validation/search budgets. | Search spaces, metrics, seeds, and reference outputs are frozen. | Planned |
| S2 — mechanism screen | Test QIA-P/L/X/A across low-data and controlled interaction-order conditions. | Matched `q`, depth, trainable-parameter bands, optimization budget, and paired seeds; include aligned and deliberately misaligned tasks. | Retain only Pareto candidates with stable validation utility and non-pathological gradients. | Planned |
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

1. Pin the public frozen encoder revision/weights digest and create the first
   dataset/split manifest; current config locks intentionally refuse execution.
2. Create the first named S0 experiment from the standard repository template,
   with its falsifiable hypothesis and reproduction command.
3. Run S0, then lock the classical search spaces and baseline artifacts in S1.

The optional provider dependencies and access checks are complete, but they do
not advance the staged experiment plan. Hardware remains gated behind the
simulator smoke test, frozen parameters, and explicit HQC authorization.

Until those actions are complete, QAtelier remains a planned parallel research
track and the production Atelier behavior remains unchanged.
