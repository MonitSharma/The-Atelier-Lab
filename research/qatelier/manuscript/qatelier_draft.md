# QAtelier: A Controlled Negative Study of Quantum Adapters on Frozen Representations

## Abstract

We study whether small parameterized quantum adapters applied to frozen
foundation-model representations provide a reproducible inductive bias beyond
strong classical controls. The protocol freezes a
`paraphrase-mpnet-base-v2` encoder, fits a shared train-only compressor, and
evaluates identical compressed inputs with strong kernel references and
parameter-matched parametric models. We cover SST-2, MRPC, CoLA, SciFact
reranking, and controlled interaction-order problems. The S0 calibration and
expanded S2 mechanism screen show quantum heads near chance and below ordinary
classical controls under the current short optimization budget. No candidate
passes the freeze gate, so no hardware jobs are submitted and no quantum
advantage claim is made. The result is a reproducible C0 negative finding that
also identifies the boundary between a valid simulator result and an
unjustified hardware campaign.

## 1. Introduction

Quantum adapters are often motivated by the possibility that a compact quantum
model can impose a useful nonlinear structure on a high-dimensional learned
representation. That possibility is easy to overstate: a quantum head can be
compared against a weak classical model, an information-leaking compressor, or
a different representation. QAtelier therefore treats classical strength,
split isolation, resource accounting, and hardware gating as part of the
scientific question.

Our primary question is whether any useful effect survives those controls. The
project is explicitly able to conclude negatively. We report the current phase
as C0 because no quantum candidate demonstrated predictive utility or a
distinct useful inductive bias.

## 2. Method

The pipeline is frozen encoder → train-only compressor → shared low-dimensional
representation → classical or quantum head. The encoder revision and weights
digest are committed in the S0 manifests. The classical ladder includes
logistic regression, linear/RBF/polynomial SVMs, RFF, matched MLP, low-rank
bilinear, and finite RBF controls. S0 and S1 use multiple low-data budgets and
five confirmation seeds.

The quantum contract defines QIA-P/L/X/A schedules, data re-uploading, exact
and finite-shot simulation, parameter serialization, and logical resource
counts. Mechanism diagnostics include kernel alignment, effective rank,
spectral summaries, and finite-difference gradient summaries.

## 3. Results

S0 contains 1,440 archived rows and shows near-chance quantum-head accuracy;
finite-shot simulation tracks exact simulation. S1 establishes the classical
reference panels before quantum screening. The controlled-order data cover
orders 1–6 across aligned, rotated, dense-misaligned, and Fourier families.

The authoritative fair-projection all-order S2 screen contains 528 rows.
Classical and quantum rows receive identical first-q feature matrices, with
row-level matrix hashes. Quantum candidates average approximately 0.497–0.498
accuracy, compared with 0.5528 across the matched classical controls. The
result does not support a candidate freeze. The earlier 456-row unequal-input
panel is retained only as rejected audit evidence.

## 4. Hardware and OOD boundary

The OOD IMDb protocol is locked but not run because no quantum candidate exists
to evaluate. IBM was limited to read-only preflight. Quantinuum was limited to
policy/discovery checks; its exact Helios-1E emulator was allowed in principle,
but no campaign was authorized. Physical Quantinuum execution is disabled by
code and configuration, and the audit records zero physical jobs.

## 5. Discussion

The result does not support a headline quantum-improvement narrative for this
current protocol. It does not prove that all quantum adapters are unhelpful.
It shows that this bounded adapter/training budget did not survive the fair
classical screen, while the broader question remains unresolved. A new study
would need a separately approved preregistration, independent seeds and
held-out evaluation, a candidate surviving noise gates, and an explicit
resource/cost justification.

## 6. Reproducibility

All current raw bundles, manifests, hashes, safety decisions, and tests are
linked from [`FINAL_RESEARCH_REPORT.md`](../FINAL_RESEARCH_REPORT.md). The
current audit reports zero provider jobs and no C1–C4 claim.
