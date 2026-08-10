# QAtelier red-team review

**Review scope:** current working tree on branch `qatelier`, reviewed against
the two governing research-plan attachments supplied for this task. The first
contains the QAtelier staged protocol and claim ladder; the second contains
the mandatory IBM/Quantinuum hardware override.
The plans were read in full. This is an independent skeptical review, not a
claim document.

**Verdict:** the repository supports a carefully scoped current-phase C0
calibration/screening report. It is not yet evidence for a general negative
result about quantum adapters and is not ready for paper submission as a
complete QAtelier study. The no-hardware decision is correct. The principal
scientific result is not yet interpretable because the expanded S2 comparison
does not give the classical and quantum models the same input information.

The working tree was not clean at review time. In addition to `HEAD` at
`2696022`, it contained modified QAtelier files and untracked S3, hardware,
report, manuscript, and test files. None of those files was changed by this
review.

## 1. Requirements satisfied

These are the requirements that are genuinely supported, with the important
scope qualifications shown below.

| Requirement | Assessment | Evidence |
| --- | --- | --- |
| Keep the work isolated from production Atelier code | Satisfied for the reviewed diff: all observed changes are under `research/qatelier/`; no production Atelier path was changed by this review. | `git status --short`; `research/qatelier/PROGRESS.md` |
| Preserve a claim ladder and allow a negative result | Satisfied. The audit and freeze artifacts explicitly support no C1–C4 claim and freeze no candidate. | `research/qatelier/audit_artifacts/audit.json`; `research/qatelier/experiments/s2_mechanism_screen/analysis/candidate_freeze.json` |
| Pin the public encoder and SST-2 data/splits | Satisfied at the manifest level. The MPNet revision, weight digest, dataset/member hashes, and deterministic split selections are recorded. | `research/qatelier/experiments/s0_reproduction/config.yaml`; `data_manifest.json`; `encoder_manifest.json`; `split_manifest.json` |
| Enforce train-only PCA in the preparation path | Satisfied in the declared implementation. `CompressorArtifact` rejects non-`train` fitting, and preparation fits each compressor from the selected training rows. | `research/qatelier/data/representations.py:56-126`; `research/qatelier/experiments/s0_reproduction/prepare_data.py:171-203`; `research/qatelier/tests/test_representations.py:9-25` |
| Archive a complete credential-free S0 run | Satisfied as a calibration artifact. The raw bundle has 1,440 rows, exact and 4,096-shot simulator tracks, 12 train selections, five confirmation seeds, eight quantum candidates, and eight classical controls. | `research/qatelier/experiments/s0_reproduction/s0_completion.json`; `raw/run_manifest.json`; `raw/results.json`; `analysis/analysis.md` |
| Separate strong references from small parametric controls | Partially satisfied. The grouping is conceptually correct and includes RBF and polynomial SVM references; the executed panels contain eight declared heads. | `research/qatelier/classical/models.py:32-43`; `research/qatelier/experiments/s1_baseline_lock/config.yaml`; `artifacts/baseline_lock_all.json` |
| Pin public S1 task definitions and reserve SciFact test qrels | Satisfied as a definition/reference-panel boundary. MRPC, CoLA, SciFact, and controlled-order artifacts are present; SciFact test qrels are explicitly unused. | `research/qatelier/experiments/s1_baseline_lock/`; `scientific_retrieval/split_manifest.json`; `scientific_retrieval/raw/run_manifest.json`; `controlled_interaction_order/manifest.json` |
| Implement deterministic circuit/resource and simulator safety tests | Largely satisfied for the NumPy logical simulator and policy layer. The schedule records qubits, gate counts, rounds, and depth; optional Aer cross-check hooks exist. | `research/qatelier/quantum_adapter.py`; `research/qatelier/simulation/simulator.py:204-372`; `research/qatelier/tests/test_simulator.py`; `research/qatelier/tests/test_quantum_adapter.py` |
| Enforce the current hardware policy | Satisfied as a guard, not as an execution campaign. Quantinuum accepts only `Helios-1E`, requires an exact cost/syntax manifest, and rejects physical execution; IBM replay requires a frozen panel. | `research/qatelier/hardware/policy.py:19-64`; `hardware/quantinuum/cost.py:20-139`; `hardware/ibm/preflight.py:102-115`; `research/qatelier/tests/test_hardware_policy.py`; `tests/test_ibm_preflight.py` |
| Avoid physical Quantinuum jobs | Satisfied. The available evidence supports zero submitted jobs, and the policy disables physical Quantinuum execution. | `research/qatelier/audit_artifacts/audit.json`; `hardware/RUN_LEDGER.csv`; `HARDWARE_ACCESS.md`; all archived `raw/run_manifest.json` files |
| Block hardware when S2 has no candidate | Satisfied as a conservative gate. The screen is marked exploratory, freezes no candidate, and authorizes no hardware. | `research/qatelier/experiments/s2_mechanism_screen/raw/orders_1_6/validation.json`; `analysis/candidate_freeze.json`; `freeze.py:23-50` |

These satisfactions should be described as current-phase infrastructure and
calibration evidence, not as completion of the full research plan.

## 2. Gaps, overclaims, and blockers

### A. Current-state and release integrity

1. **The dedicated QAtelier test suite is not green.** The read-only command
   `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -q research/qatelier/tests`
   returned exit code 1: 84 passed, 4 failed, and 7 benchmark subtests passed.
   The failures are in `research/qatelier/tests/test_cli.py:7-66`:
   three tests still expect unresolved-placeholder/structure-only behavior,
   while the current working-tree config and CLI report execution-ready; the
   fourth expects the phrase `execution blocked`, while the CLI emits
   `quantum is not implemented in P0`. This is an inconsistent implementation/
   test state, not evidence of a green suite. Do not repair this by weakening
   the tests without deciding which protocol semantics are authoritative.

2. **The progress and final-release claims are ahead of the checked state.**
   The working-tree `PROGRESS.md` says 87 tests pass, but the current run does
   not. `FINAL_RESEARCH_REPORT.md`, the manuscript, S3 files, and hardware
   ledger are untracked at review time; `git ls-tree HEAD research/qatelier`
   does not contain them. The report's “current audited commit: 2696022” is
   therefore not a complete description of the current working tree.

3. **S0 documentation overstates artifact completeness.** The modified S0
   README says cached embedding/compressor hashes are committed, but
   `preparation_validation.json` says
   `artifact_storage: external_output_directory_only`, and the repository does
   not contain the corresponding embedding cache or fitted PCA `.npz` files.
   `s0_completion.json` hashes the raw result and analysis, not the external
   representation bytes. A fresh clone cannot reproduce the archived S0
   numbers from the committed tree alone.

4. **The advertised reproduction commands are not the full reproduction
   path.** `Makefile:16-53` routes `qatelier-baselines`, `qatelier-screen`,
   `qatelier-heldout`, `qatelier-noise`, `qatelier-paper`, `qatelier-audit`,
   and `qatelier-reproduce` through reserved CLI commands. The CLI explicitly
   raises “not implemented in P0” for those stages at `research/qatelier/cli.py:225-230`.
   CI does run a dedicated QAtelier test step (`.github/workflows/test.yml:36-43`),
   which is good, but that step currently fails in this working tree.

### B. Frozen representations and compressor auditability

The protocol intent is strong, but the evidence is not yet sufficient for a
paper-grade leakage audit.

1. The train-only fit is implemented correctly in the normal preparation path:
   `prepare_data.py:175-187` selects training rows and `representations.py:95-126`
   fits only those rows. The MRPC/CoLA/SciFact preparation manifests also label
   compressors `fit_split: train`.

2. `CompressorArtifact.load()` validates that serialized metadata round-trips
   (`representations.py:161-183`) but does not recompute `artifact_hash`,
   `fit_features_hash`, or `fit_sample_ids_hash` from the loaded arrays and
   the declared split. The S1 runners load a compressor and transform data
   (`experiments/s1_baseline_lock/run_classical.py:74-89`) without independently
   verifying that those hashes equal the selected training matrix. This does
   not prove that leakage occurred; it means the current verifier cannot prove
   that an external compressor was fitted on exactly the declared rows.

3. The cached embeddings, pair features, and fitted compressors for the
   archived S1 panels are likewise external-only. The raw manifests hash an
   external preparation manifest, but the audit does not include the external
   arrays or fitted-object bytes. The paper must either commit immutable,
   distributable artifacts or provide a clean-download/rebuild verifier that
   recomputes every fit hash from the pinned source and split manifests.

4. The frozen encoder itself is not a leakage concern merely because all rows
   are encoded: it is declared frozen and not fine-tuned. The remaining risk is
   provenance of the downstream compressor and pair-feature caches, which must
   be checked independently before using “leakage-free” as a result claim.

### C. Classical baseline strength and fairness

1. The executed raw panels contain exactly these eight heads:
   `rbf_svm`, `polynomial_svm`, `logistic`, `linear_svm`, `rff`,
   `matched_mlp`, `low_rank_bilinear`, and `finite_rbf`. The required MPS/
   tensor-network and spectrum/Fourier-matched controls are not present in any
   executed S1 or S2 panel. Their names in the model registry
   (`classical/models.py:32-43`) are not evidence that they were run.

2. The small controls are trained once per declared split with fixed options,
   e.g. `run_classical.py:18-28` and `:82-89`; the manifests do not document a
   validation-based hyperparameter search budget or equal selection budget for
   all heads. RBF/polynomial SVMs are valid strong references, but the
   parameter-matched group should not be presented as a fully tuned fairness
   control until parameter counts, optimization budgets, and selection rules
   are reported side by side.

3. In S2, the fairness problem is more serious. The classical controls are
   trained on all six features at `s2_mechanism_screen/screen.py:67-69`, while
   each quantum model is trained and evaluated on `features[:, :q]` at
   `:77-79` for `q` in `{2,4}`. The aggregate classical mean in
   `freeze.py:35-45` is therefore not a representation-matched quantum-versus-
   classical comparison. The quantum underperformance cannot be interpreted
   as a quantum inductive-bias result until both sides receive the same
   information (or a predeclared, matched projection/compressor).

4. S0/S2 quantum optimization is also much shorter than the classical fitting
   procedures: S0 declares eight finite-difference steps and S2 declares only
   two (`s2_mechanism_screen/config_orders_1_6.yaml`). The honest conclusion
   is optimization-budget-limited performance under the tested protocol, not
   that the quantum hypothesis class is intrinsically inferior.

### D. S1 task and test/OOD separation

1. S1 is explicitly partial. `artifacts/baseline_lock_all.json` says
   `status: partial_multitask_reference_lock`, while the S1 README says the
   controlled-order condition remains open. The aggregate artifact contains
   useful reference panels, but “S1 classical baseline lock complete” is an
   overclaim. Use “classical reference panels archived” until a single coherent
   lock artifact and selection protocol exist.

2. SciFact correctly reserves test qrels and records `test_qrels_used: false`.
   However, the governing plan requires a fixed BM25/dense/hybrid candidate
   retrieval pool followed by top-K reranking. The current runner scores the
   entire 5,183-document corpus for every confirmation query
   (`scientific_retrieval/run_classical.py:103-111`), and the config calls this
   `full_5183_document_corpus`. That is a valid full-corpus ranking experiment,
   but it is not the specified candidate-reranking pipeline and must not be
   described as one. Hard-negative pair accuracy and an identical top-K pool
   are also absent.

3. The S1 classification panels evaluate confirmation selections, not an
   independently held-out final test. This is acceptable for a pre-screening
   reference panel only if no model/architecture is selected from those
   numbers. It is insufficient for a final predictive claim. The controlled
   order artifact has train and confirmation splits but no separate final test
   split. SciFact has reserved test qrels, but they were not executed.

4. The S3 IMDb OOD manifest is a useful locked protocol, but its decision
   explicitly says it was not executed because no candidate was frozen.
   Therefore no current artifact supports an OOD result or an ID-to-OOD
   degradation claim. The same applies to S3 held-out simulator results.

### E. S2 mechanism screen is exploratory, not a valid mechanism conclusion

1. The all-order panel covers only `q={2,4}` and uses two training steps;
   `q=6` was not retained and `q=8` is not possible under the six-feature
   screen. This is narrower than the governing staged screen and should be
   labeled bounded exploratory work.

2. The screen creates a different problem seed for each order
   (`screen.py:51-55`, `problem_seed + order`). Consequently, an apparent
   change with interaction order is confounded with a changed target
   realization. The controlled-order generator has the analogous per-order
   seed construction at `controlled_interaction_order/generate.py:90-92` and
   `:146-169`. For an order-effect figure, freeze the target directions and
   vary only the order, or explicitly model target realization as a factor.

3. There is one train seed, one evaluation seed, and one short optimization
   run per condition. The reported `n=24` for a candidate is the number of
   heterogeneous family/order cells, not 24 independent replications of one
   estimand. The freeze compares pooled means, not paired deltas with
   uncertainty. No multiple-testing correction or preregistered Pareto
   selection is implemented.

4. The required mechanism controls are incomplete: no executed MPS/tensor
   control, no spectrum-matched classical surrogate, no scrambled graph with
   matched edge count, no random-parameter control, and no permuted-label
   control. The existing line spectral diagnostic is a one-dimensional line
   scan (`screen.py:80-85`), not a characterization of the trained PQC's
   multivariate Fourier support.

5. The raw S2 summary gives exactly the same aggregate accuracies for all 16
   quantum IDs within each re-upload count, despite different circuit
   resources and parameter hashes (`raw/orders_1_6/summary.md` and
   `raw/orders_1_6/results.json`). QIA-X/P and QIA-A/L degeneracies at `q=2`
   are expected from the declared graph definitions, but the exact equality
   across q, topology, and family is sufficiently suspicious to require a
   technical audit of feature use, readout, initialization, and training before
   publication. It should not be used as evidence that all topologies behave
   identically.

6. S2 has no finite-shot/noise condition. S0's finite-shot track is useful
   calibration, but it is not the S4 fixed-candidate noise screen required by
   the plan.

### F. Statistics and reporting

1. S1 and S2 reports primarily provide means and sample standard deviations.
   They do not provide paired quantum-versus-classical confidence intervals,
   effect sizes, failed-run accounting, or multiple-comparison correction at
   the mechanism-screen level. `baseline_lock_all.md` and
   `s2_mechanism_screen/raw/orders_1_6/summary.md` are descriptive tables, not
   inferential analyses.

2. S0 does compute a 2,000-replicate bootstrap, but it pools rows across
   budgets, training selections, and confirmation seeds in
   `s0_reproduction/analysis.py:24-36` and `:102-126`. A paper analysis should
   use a declared clustered/paired bootstrap or hierarchical model, with the
   experimental unit stated explicitly. The current analysis does not correct
   for the many candidate comparisons.

3. The required complete learning-curve statistic (for example normalized
   area under the curve), calibration/AUROC where appropriate, and resource-
   performance frontiers are not generated for the current panels. A single
   pooled accuracy cannot support a sample-efficiency or OOD narrative.

### G. IBM and Quantinuum policy/evidence

1. The safety direction is correct: no IBM circuit job, no Helios-1E emulator
   campaign, and zero physical Quantinuum jobs. Quantinuum syntax/cost checks
   were not run because no campaign was authorized; that is compliant with the
   gate, but it is not emulator validation.

2. The field `provider_contacted: false` in the experiment audit is ambiguous
   and, literally, contradicted by `HARDWARE_ACCESS.md`, which records a
   successful IBM authentication/backend metadata check and a successful
   Nexus login/device discovery. The accurate distinction is: **no scientific
   circuit submissions or shots; read-only provider preflight/discovery did
   contact the services**. The audit and paper should use separate fields for
   `preflight_contacted`, `circuit_jobs_submitted`, and `physical_quantinuum_jobs`.

3. The policy and cost-manifest guards are implemented, but there is no actual
   IBM execution adapter, Quantinuum emulator submission/recovery path, raw
   provider response archive, or compiled-resource campaign in the current
   tree. That is acceptable while no candidate exists; it prevents any claim
   of S5/S6 completion.

4. The current evidence does not justify an IBM-versus-Quantinuum hardware
   comparison. If the study is extended, the manuscript must say “IBM physical
   QPU” versus “Quantinuum Helios-1E emulator,” and must never call the latter
   physical hardware under the mandatory override.

## 3. Exact evidence paths

The following paths are the authoritative artifacts inspected for this review.
Paths are repository-relative unless an absolute plan path is shown.

### Governing requirements

- Governing research-plan attachment 1 — full research plan, especially P0,
  S0–S4, red-team, acceptance test, and final product definition.
- Governing research-plan attachment 2 — mandatory IBM/Quantinuum override,
  emulator-only policy, cost gate, and zero-physical-Quantinuum requirement.

### Current-phase claims and release state

- `research/qatelier/PROGRESS.md`
- `research/qatelier/audit_artifacts/audit.json`
- `research/qatelier/audit_artifacts/audit.md`
- `research/qatelier/FINAL_RESEARCH_REPORT.md` (untracked at review time)
- `research/qatelier/manuscript/qatelier_draft.md` (untracked at review time)
- `research/qatelier/manuscript/REPRODUCIBILITY_APPENDIX.md` (untracked at
  review time)
- `research/qatelier/audit.py`

### S0

- `research/qatelier/experiments/s0_reproduction/config.yaml`
- `research/qatelier/experiments/s0_reproduction/data_manifest.json`
- `research/qatelier/experiments/s0_reproduction/encoder_manifest.json`
- `research/qatelier/experiments/s0_reproduction/split_manifest.json`
- `research/qatelier/experiments/s0_reproduction/prepare_data.py:82-203`
- `research/qatelier/experiments/s0_reproduction/execution.py:225-333`
- `research/qatelier/experiments/s0_reproduction/raw/results.json`
- `research/qatelier/experiments/s0_reproduction/raw/run_manifest.json`
- `research/qatelier/experiments/s0_reproduction/s0_completion.json`
- `research/qatelier/experiments/s0_reproduction/analysis.py`
  (the implementation is at the S0 directory root)
- `research/qatelier/experiments/s0_reproduction/analysis/analysis.json`
- `research/qatelier/experiments/s0_reproduction/analysis/analysis.md`
- `research/qatelier/experiments/s0_reproduction/preparation_validation.json`

### S1 and representations

- `research/qatelier/data/representations.py:56-183`
- `research/qatelier/experiments/s1_baseline_lock/config.yaml`
- `research/qatelier/experiments/s1_baseline_lock/artifacts/baseline_lock_all.json`
- `research/qatelier/experiments/s1_baseline_lock/artifacts/baseline_lock_all.md`
- `research/qatelier/experiments/s1_baseline_lock/run_classical.py:31-93`
- `research/qatelier/experiments/s1_baseline_lock/raw/mrpc/`
- `research/qatelier/experiments/s1_baseline_lock/raw/cola/`
- `research/qatelier/experiments/s1_baseline_lock/scientific_retrieval/README.md`
- `research/qatelier/experiments/s1_baseline_lock/scientific_retrieval/run_classical.py:49-114`
- `research/qatelier/experiments/s1_baseline_lock/scientific_retrieval/raw/`
- `research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order/README.md`
- `research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order/generate.py`
- `research/qatelier/experiments/s1_baseline_lock/controlled_interaction_order/raw/`
- `research/qatelier/tests/test_representations.py`
- `research/qatelier/tests/test_s1_baseline_lock.py`
- `research/qatelier/tests/test_s1_scientific_retrieval.py`
- `research/qatelier/tests/test_s1_controlled_order.py`

### S2 and held-out boundary

- `research/qatelier/experiments/s2_mechanism_screen/config_orders_1_6.yaml`
- `research/qatelier/experiments/s2_mechanism_screen/screen.py:42-88`
- `research/qatelier/experiments/s2_mechanism_screen/freeze.py:13-66`
- `research/qatelier/experiments/s2_mechanism_screen/raw/orders_1_6/`
- `research/qatelier/experiments/s2_mechanism_screen/analysis/candidate_freeze.json`
- `research/qatelier/experiments/s2_mechanism_screen/analysis/candidate_freeze.md`
- `research/qatelier/experiments/s3_heldout/` (untracked at review time;
  protocol locked, not executed)

### Tests, CI, and commands

- `research/qatelier/tests/test_cli.py:7-66`
- `research/qatelier/tests/test_config.py` (modified at review time)
- `research/qatelier/tests/test_s2_screen.py`
- `research/qatelier/tests/test_hardware_policy.py`
- `research/qatelier/tests/test_ibm_preflight.py`
- `.github/workflows/test.yml:30-47`
- `Makefile:16-53`
- `research/qatelier/cli.py:94-115,225-254`

### Hardware

- `research/qatelier/HARDWARE_ACCESS.md`
- `research/qatelier/hardware/policy.py:19-125`
- `research/qatelier/hardware/quantinuum/cost.py:20-139`
- `research/qatelier/hardware/ibm/preflight.py:32-115`
- `research/qatelier/hardware/RUN_LEDGER.csv` (untracked at review time)
- `research/qatelier/hardware/HARDWARE_DECISIONS.md` (untracked at review
  time)
- `research/qatelier/hardware/PHYSICAL_QUANTINUUM_DECISION.md` (untracked at
  review time)

## 4. Recommendations before paper submission

### Must fix before making a scientific headline claim

1. **Resolve the working tree and test contract.** Decide whether the locked
   current-phase config is intended to be execution-ready, update the CLI/tests
   consistently, run the dedicated suite to zero failures, and regenerate the
   audit from the same committed tree. Do not describe 87 passing tests while
   the command returns four failures.

2. **Correct S2 information matching.** Give classical and quantum heads the
   identical six-to-`q` representation, or fit and freeze one train-only
   projection per declared condition and pass that exact matrix to every head.
   Add a test that hashes the feature matrix received by each model. Hold the
   latent target directions fixed when comparing interaction order, and add
   independent model/split seeds.

3. **Re-run a sufficiently powered mechanism screen.** Use a validation split
   for selection, an untouched final test split, a declared optimization
   budget shared fairly enough to interpret, and paired clustered uncertainty.
   Explain or fix the exact equality of the quantum summaries before retaining
   any topology conclusion.

4. **Add the required classical mechanism controls.** Run an MPS/tensor-network
   control where practical and a spectrum/Fourier-matched surrogate with
   support and coefficient-budget hashes. Add explicit entanglement graph,
   scrambled-graph, random-parameter, and permuted-label ablations.

5. **Make the compressor audit independently verifiable.** Commit the fitted
   objects and hashes where licensing permits, or provide a clean-room
   preparation command that downloads the exact pinned inputs and recomputes
   `fit_sample_ids_hash`, `fit_features_hash`, and the full artifact hash. Make
   the verifier inspect array bytes, not only self-consistent metadata.

6. **Finish test/OOD separation before reporting performance.** Keep SciFact
   test qrels untouched, implement the fixed candidate-retrieval/top-K
   reranking protocol, and do not call confirmation accuracy a final test
   result. Execute the locked IMDb OOD and final held-out panel only after a
   candidate and parameters are frozen; otherwise state explicitly that no OOD
   result exists.

7. **Upgrade the statistical package.** Report per-seed values, paired
   differences against the strongest reference and each matched control,
   clustered bootstrap/CIs, effect sizes, failed runs, complete learning
   curves/AUC, and a predeclared multiple-testing correction. Report resource
   and wall-time quantities alongside accuracy.

### Hardware-specific requirements for any future extension

8. Keep the present stop decision. Do not submit IBM or Quantinuum circuits
   without a frozen simulator candidate and a documented gate. If a future
   gate passes, distinguish read-only provider preflight from scientific jobs;
   use IBM only for frozen replay, require the official Helios-1E syntax/resource
   check and immutable estimated-HQC manifest before every emulator campaign,
   and keep physical Quantinuum execution disabled.

9. Do not call the present branch hardware-validated. A future report must
   include the IBM backend/transpilation/resource record, Helios-1E emulator
   raw results and cost record, and a separate physical-Quantinuum status of
   zero. Never infer energy from gates, queue time, or HQCs.

### Release and paper package

10. Commit or explicitly remove the untracked final report, manuscript,
    S3 protocol, and hardware ledger; make the claim-to-evidence map hash every
    headline input; add figures/tables generated from committed raw artifacts;
    and test the credential-free reproduction from a fresh clone and clean
    environment. The paper title and abstract should say “current-phase,
    short-budget C0 calibration/screen” unless the fairness and held-out gaps
    above are closed.

## Bottom line

The branch shows disciplined safety engineering and a useful negative
calibration outcome. It does **not** yet show that quantum adapters lose after a
fair representation-matched mechanism study, nor that they provide no useful
inductive bias in general. The defensible submission-level statement today is:

> Under the current frozen MPNet/SST-2 calibration and bounded, short-budget
> exploratory S2 implementation, no quantum candidate demonstrated utility and
> no hardware campaign was authorized; the broader QAtelier research question
> remains unresolved.

## 5. Resolution recorded on `qatelier`

The review's primary comparison blocker was fixed before release packaging:

- the original 456-row unequal-information panel is retained under
  `raw/orders_1_6/` and marked rejected;
- the authoritative rerun is `raw/orders_1_6_fair/` with 528 rows, 144 matched
  classical rows, and 384 quantum rows;
- both model families receive the same first-q matrix, and every row records
  train/evaluation matrix hashes;
- the corrected aggregate is 0.5528 classical accuracy versus approximately
  0.497–0.498 for the quantum rows, with no candidate frozen;
- the focused suite now passes 88 tests plus 7 benchmark subtests, and the
  audit is regenerated from the corrected report and freeze artifact.

The remaining limitations above are intentionally preserved in the final
report: this is a scoped C0 current-phase result, not a general negative claim
or a completed held-out/hardware study.
