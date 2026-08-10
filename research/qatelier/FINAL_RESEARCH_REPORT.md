# QAtelier final current-phase research report

Status: `C0 — no demonstrated quantum benefit`.

Branch: `qatelier`
Audit record: [`audit_artifacts/audit.json`](audit_artifacts/audit.json)
Date: 2026-08-10

## Executive conclusion

QAtelier tested whether a small parameterized quantum adapter applied to frozen
foundation-model representations showed a reproducible benefit beyond strong
representation-matched classical controls. In the completed current phase, the
answer is negative.

The quantum heads were near chance in the S0 calibration and bounded S2
mechanism screen, while ordinary classical controls performed better. No
quantum candidate survived the freeze gate. Consequently:

- no C1 predictive-utility claim is supported;
- no C2 distinct-inductive-bias claim is supported;
- no C3 hardware-survival claim is supported;
- no C4 computational quantum-advantage claim is supported;
- IBM physical jobs submitted: `0`;
- Quantinuum Helios-1E emulator jobs submitted: `0`;
- Quantinuum physical jobs submitted: `0`.

This is a scoped current-phase C0 calibration/screening result, not evidence
that all quantum adapters fail. The repository preserves the protocol, raw
results, controls, hashes, decision gates, and reproduction checks needed to
support that limited conclusion.

## Research question and claim ceiling

The question was:

> Does a small parameterized quantum adapter operating on frozen
> foundation-model representations exhibit useful and reproducible inductive
> bias beyond strong representation-matched classical models in low-data,
> distribution-shift, and controlled high-order-interaction regimes, and does
> any such effect survive real hardware?

The claim ladder was C0 through C4. The current evidence reaches C0 only. The
project deliberately does not equate a win over a weak classical model with
quantum advantage, and it does not treat parameter matching as a substitute
for strong nonlinear classical references.

## Frozen protocol

The public canonical encoder was
`sentence-transformers/paraphrase-mpnet-base-v2`, revision
`6cc9279c672dc57f94445ef259b28a1b736fec8f`, with weights digest
`5fc2279bd6e503ca3543197b4ef00b615d87eebd02490f8c108aa3f35d7b705d`.
Embeddings were not fine-tuned. Compressors were fitted only on training
selections and reused by every head receiving the corresponding representation.

Classical controls were separated into:

- strong unconstrained references: RBF SVM and polynomial SVM;
- parameter-matched controls: logistic regression, linear SVM, RFF, matched
  MLP, low-rank bilinear, and finite RBF.

The task and split manifests use deterministic training selections and five
confirmation seeds. SciFact records a frozen full-corpus ranking panel; it is
not the planned fixed candidate-pool/top-K reranking experiment, and its
reserved test qrels were not used.

## Completed evidence

### S0 calibration

The archived S0 bundle contains 1,440 rows across 12 training selections, five
confirmation seeds, eight quantum candidates, and eight classical controls at
q=2 and q=4. Exact and finite-shot simulator metrics were both recorded.
Finite-shot results tracked exact simulation closely, but the quantum heads
were near chance and below the classical controls. The result is explicitly
labelled calibration-only.

Evidence: [`experiments/s0_reproduction/analysis/analysis.md`](experiments/s0_reproduction/analysis/analysis.md),
[`experiments/s0_reproduction/s0_completion.json`](experiments/s0_reproduction/s0_completion.json).

### S1 classical reference panels

The following panels are archived without provider execution:

| Condition | Rows | Notes |
| --- | ---: | --- |
| SST-2 | 1,440 S0-derived rows | Frozen MPNet, shared compressor, exact/finite-shot calibration |
| MRPC | 480 | Pair representation, eight classical heads, five confirmation seeds |
| CoLA | 480 | Frozen sentence representation, eight classical heads |
| SciFact | 360 | Nine train-only representations × five confirmation seeds × eight heads; test qrels unused |
| Controlled order | 14,400 | 24 family/order problems × five budgets × five confirmation seeds × eight heads |

Evidence: [`experiments/s1_baseline_lock/`](experiments/s1_baseline_lock/),
[`experiments/s1_baseline_lock/artifacts/baseline_lock_all.md`](experiments/s1_baseline_lock/artifacts/baseline_lock_all.md).

### S2 mechanism screen

The authoritative fair-projection panel contains 528 rows covering four
synthetic families, interaction orders 1–6, q=2/4, QIA-P/L/X/A, both re-upload
counts, and three classical controls per q. Classical and quantum rows receive
the identical first-q feature matrix; the row-level train/evaluation hashes
make this checkable. Aggregate classical accuracy is 0.5528, while quantum
candidates are approximately 0.497–0.498. The short two-step screen is
treated as a bounded exploratory gate, not as a universal theorem about all
quantum circuits. The earlier unequal-information 456-row panel is preserved
as rejected audit evidence and is not used here.

Evidence: [`experiments/s2_mechanism_screen/raw/orders_1_6_fair/`](experiments/s2_mechanism_screen/raw/orders_1_6_fair/),
[`experiments/s2_mechanism_screen/analysis/candidate_freeze.md`](experiments/s2_mechanism_screen/analysis/candidate_freeze.md).

## Held-out and OOD status

The S3 OOD protocol is locked for SST-2 → IMDb sentiment transfer, including
the IMDb revision, file hashes, label mapping, and test-only rule. It was not
executed because S2 froze no quantum candidate. Running OOD evaluation without
a frozen quantum model would not be a valid comparison.

Evidence: [`experiments/s3_heldout/`](experiments/s3_heldout/).

## Hardware status

IBM credentials and backend metadata were checked read-only. This preflight
contacted the provider service but submitted no physical IBM job because the
freeze gate did not pass.

Quantinuum authentication and the exact `Helios-1E` emulator identifier were
verified earlier in the phase. No emulator campaign was submitted because no
candidate was frozen. Physical Quantinuum execution was disabled in code and
configuration for the entire phase.

Required final wording:

```text
IBM physical QPU:
not executed; no candidate passed the simulator freeze gate

Quantinuum syntax/resource checks:
not run for a campaign; no candidate was authorized

Quantinuum Helios-1E emulator:
not executed; no candidate was frozen

Quantinuum physical QPU:
NOT EXECUTED BY DESIGN

Future physical Quantinuum decision:
DEFERRED UNTIL REVIEW OF CURRENT RESULTS
```

Evidence: [`hardware/RUN_LEDGER.csv`](hardware/RUN_LEDGER.csv),
[`hardware/HARDWARE_DECISIONS.md`](hardware/HARDWARE_DECISIONS.md),
[`hardware/PHYSICAL_QUANTINUUM_DECISION.md`](hardware/PHYSICAL_QUANTINUUM_DECISION.md),
[`audit_artifacts/audit.json`](audit_artifacts/audit.json).

## Limitations

The current negative result does not establish that every possible QAtelier
architecture or training procedure fails. The expanded screen used short
optimization budgets and one train/evaluation realization per family/order
cell, and q=6 was documented but not completed because the finite-difference
simulator was impractical at that grid size. The S1 panels are reference
panels rather than a single held-out multitask lock; SciFact used full-corpus
ranking instead of the planned top-K candidate reranker. S3 OOD and S4 noise
campaigns were not run because no candidate passed the gate. These are
explicit scope boundaries, not omitted results.

The heterogeneous S1 tasks use task-appropriate metrics, so the aggregate lock
table is a provenance table rather than a single cross-task leaderboard.

## Reproduction and audit commands

From the repository root:

```bash
make qatelier-reproduce
python3 -m ruff check research/qatelier
python3 scripts/check_repo.py
python3 scripts/validate_experiments.py
python3 -m research.qatelier.cli validate --json
```

The current-phase audit is generated with:

```bash
python3 -m research.qatelier.audit --output-dir /tmp/qatelier-audit
```

The generated audit must report `provider_jobs=0`,
`physical_quantinuum_jobs=0`, no frozen candidates, and no C1–C4 claim.

## Final claim

Under the declared frozen-representation, shared-compressor, strong-classical,
low-data, and bounded fair-projection simulator screen, QAtelier did not
demonstrate a useful reproducible quantum-adapter benefit in the current phase.
The scientifically appropriate conclusion is a scoped C0 result, with the
broader research question unresolved and further hardware/OOD execution
deferred until a separately approved preregistration produces a candidate that
survives the classical and simulator gates.
