# QAtelier architecture

> Status: implemented current-phase research design. This document describes
> the experimental system; it does not claim a quantum advantage or authorize
> production integration.

## Research question and hypothesis

QAtelier asks whether a small parameterized quantum head can provide a useful,
measurable inductive bias when it adapts frozen foundation-model
representations, especially in low-data, out-of-distribution (OOD), and
controlled high-order-interaction settings.

The falsifiable hypothesis is:

> After representation, compression, parameter count, training data, and
> validation budget are matched, a quantum head improves the pre-registered
> sample-efficiency or OOD metric on at least one defined regime, and the
> improvement tracks a circuit/mechanism variable rather than a weak baseline
> or a compression artifact.

A null result is valid: if strong classical nonlinear or spectrum-matched
 baselines remove the effect, the result should be recorded as evidence about
 the limits of the proposed quantum inductive bias.

## System under test

The controlled path is:

```text
input x
  -> frozen foundation encoder h_phi
  -> embedding e in R^D
  -> shared train-split-only compressor C
  -> compressed representation z in R^q
  ->+ classical head(s)       -> prediction / relevance score
    + quantum head (PQC)     -> prediction / relevance score
```

The encoder is fixed before any head is trained:

```text
e = h_phi(x)
z = C(e)
```

`h_phi` is the selected foundation or sentence-embedding model. Its weights,
tokenization, pooling rule, model revision, and inference settings are frozen
and recorded. For query-document reranking, construct the pair representation
before compression, for example `[e_q; e_d; |e_q - e_d|; e_q * e_d]`, then apply
the same `C` to every head.

`C` is the shared bottleneck that removes the input-size confound. The primary
version is unsupervised PCA or whitening fitted on training embeddings only,
then frozen and reused by every competing head. A learned compressor is a
separate secondary condition, never an unreported advantage for the quantum
model.

## Competing heads

### Classical reference heads

Every head receives the same `z`, labels, split, and search budget. The minimum
reference ladder is:

- logistic regression and linear SVM as linear sanity checks;
- RBF and polynomial SVMs as strong low-dimensional nonlinear controls;
- random Fourier features with a linear readout;
- a small MLP across declared parameter-count bands;
- low-rank bilinear or tensor-network/MPS models where the task needs
  interactions;
- a spectrum-matched classical surrogate when the quantum circuit's accessible
  Fourier support can be estimated.

The existing Atelier router may be an application incumbent, but it is not a
parameter-matched toy baseline. Keep its task and training cost distinct.

### Quantum head

The initial family uses angle encoding and data re-uploading. A minimal binary
form is:

```text
E(z) = tensor_i RY(z_i) RZ(eta_i z_i)
U_theta(z) = product_l V_l(theta_l) E(z)
f_theta(z) = <0| U_theta(z)^dagger O U_theta(z) |0>
p(y=1|x) = (1 - f_theta(z)) / 2
```

The implementation must state the exact encoding, trainable scale, circuit
depth `L`, re-upload count `R`, qubit count `q`, entanglement graph `G`,
observables, readout parameters, initialization, and simulator/backend. The
first ablation families are:

| Family | Entanglement | Purpose |
| --- | --- | --- |
| QIA-P | Product / none | Isolate single-qubit nonlinearities and re-uploading. |
| QIA-L | Shallow local graph | Hardware-friendly interaction control. |
| QIA-X | Predeclared long-range pairs | Test cross-feature interactions. |
| QIA-A | Small dense schedule | Expressivity probe; not assumed hardware-efficient. |

For multiclass tasks, use multiple declared observables plus a small linear
readout and count those parameters. Do not treat the Hilbert-space dimension as
an ML resource advantage by itself; state preparation, trainability, readout,
shots, compilation, and classical simulation cost are part of the comparison.

## Evaluation ladder

Claims stop at the strongest level supported by the measurements:

| Level | Permitted interpretation | Required evidence |
| --- | --- | --- |
| C0 | No demonstrated benefit / parity | No consistent win after matched controls. |
| C1 | Quantum-head utility | Repeated-seed effect on pre-registered tasks, with uncertainty intervals. |
| C2 | Distinct inductive bias | Effect follows interaction order, spectrum, entanglement, or another declared mechanism and survives strong classical surrogates. |
| C3 | Hardware-supported utility | Frozen selected parameters retain the effect on IBM and/or Quantinuum with noise and resource accounting. |
| C4 | Computational quantum advantage | A defensible scaling or hardness separation against relevant classical algorithms; not an expected baseline outcome. |

Accuracy on one dataset, a best seed, or a win over only a linear baseline is
not sufficient for C1, and no result should use “quantum advantage” language
without C4 evidence.

## Scope boundaries

In scope:

- frozen classical representations with a shared low-dimensional compressor;
- few-shot classification, scientific retrieval/reranking, and controlled
  interaction-order tasks;
- matched classical heads and quantum circuit families;
- Fourier/kernel/gradient diagnostics and parameter, shot, runtime, and
  compiled-resource accounting;
- simulation-first selection followed by frozen-parameter hardware validation.

Out of scope for the initial branch:

- end-to-end quantum language-model training or changing the production
  embedder, router, retrieval path, or agent behavior;
- replacing candidate retrieval with a quantum circuit; reranking starts after
  the classical candidate pool is formed;
- broad QPU hyperparameter search, hardware-in-the-loop training, or
  post-hoc mitigation tuning on test labels;
- generic claims about quantum advantage, energy superiority, or exponential
  Hilbert-space dimension;
- copying the private source DOCX or adding external citations without a
  verification record;
- adding an experiment registry entry before an experiment has a committed
  question, status, location, and reproduction command.

## Experiment contract

Each future experiment should follow the repository's standard experiment
shape: question and hypothesis; controls and changed variable; hardware,
software, and seed; metrics and artifacts; observation and limitations; and
reproduction. Use a named experiment directory with `config.yaml`, an explicit
runner and analysis entry point, raw outputs under `raw/`, and figures under
`figures/`. Keep all result values traceable to committed raw artifacts; do not
fill missing fields by inference.
