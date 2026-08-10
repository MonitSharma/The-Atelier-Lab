# QAtelier literature and novelty audit

Audit date: 2026-08-10
Scope: Workstream A only; no experimental outputs, central configuration, registry, or progress files were changed.

## Audit standard

This is a targeted primary-source audit, not a claim of exhaustive systematic-review coverage. I searched and checked the original paper, proceedings, journal, publisher, or author-maintained preprint record for each included item. The BibTeX record and the source URL are paired in `references.bib`; the factual scope and limitation of each source are recorded in `literature_matrix.csv`.

The audit prioritizes primary sources over reviews, news articles, and secondary summaries. A preprint is labeled as a preprint even when it reports hardware results. Bibliographic fields were omitted where the verified primary record did not expose them; no publication venue, page range, DOI, result, or hardware claim has been filled from inference.

## What is already established

### Quantum fine-tuning and adapter precedents

Kim et al. study a frozen classical sentence-transformer followed by a parameterized quantum classification stage, with low-data sentiment experiments, finite shots, noisy simulations, and classical controls [@Kim2025QLLMFineTuning]. This is the closest direct precedent for QAtelier's S0 calibration, but its finite screened study is not a controlled demonstration of a general quantum advantage. In particular, its use of active support-vector count as an effective SVC parameter count is explicitly not a one-to-one capacity equivalence [@Kim2025QLLMFineTuning].

Knitter et al. extend this line toward direct energy-to-solution instrumentation on trapped-ion hardware and compare the hybrid pipeline with classical models and tensor-network methods [@Knitter2026EnergyFineTuning]. The result makes energy measurement a legitimate separate research question, but it does not justify estimating whole-system energy from circuit size, gate count, or provider service time.

The 2026 Cayley-adapter preprint places quantum circuit blocks inside frozen projection layers and reports IBM physical-QPU inference for Llama 3.1 8B, together with a smaller SmolLM2 study [@Aizpurua2026CayleyAdapters]. QCHFT proposes MPS-PQC, pairwise-contraction, and LinearA--Quantum--LinearB adapter families for an IoT resource-allocation task and compares them with LoRA [@Li2026QCHFT]. QuanTA is an important neighboring method because it uses quantum-inspired tensor structure but is a classical high-rank adaptation method without quantum inference overhead [@Chen2024QuanTA].

These sources establish that the broad idea “insert a small structured adapter into a frozen or mostly frozen foundation model” is not novel by itself. QAtelier must therefore avoid presenting a small PQC head, QCHFT-like contraction structure, Cayley/unitary parameterization, or quantum-inspired tensor parameterization as a standalone contribution.

### Quantum feature maps, kernels, and classical equivalence

Quantum feature-space work formalizes data encoding as a feature map into a quantum Hilbert space and connects kernel estimation with classical kernel learning [@Schuld2019FeatureHilbertSpaces; @Havlicek2019QuantumFeatureSpaces]. The relevant scientific question is not whether the feature space is large, but whether its target-aligned bias is useful and difficult to reproduce at the relevant resource scale.

Huang et al. show that data can make classical learners competitive with quantum models, while engineered, target-aligned projected quantum kernels can create separations in specific settings [@Huang2021PowerOfData]. Kübler et al. sharpen the inductive-bias criterion: a plausible advantage requires a low-dimensional, target-aligned kernel whose useful bias is hard to encode classically, while kernel evaluation itself can become measurement-expensive [@Kubler2021InductiveBias]. Slattery et al. report numerical evidence that common tuning can make several quantum fidelity kernels well approximated by classical kernels on classical data [@Slattery2023NumericalEvidence].

Jerbi et al. provide a model taxonomy in which explicit, kernel/implicit, and data-re-uploading models have different qubit and sample requirements [@Jerbi2023BeyondKernelMethods]. This prevents QAtelier from treating a variational circuit, a kernel model, and a classical surrogate as interchangeable just because they share a qubit count or parameter count.

### Data re-uploading and Fourier characterization

Pérez-Salinas et al. introduce repeated data encoding interleaved with trainable processing and show a universal-classifier construction [@PerezSalinas2020DataReuploading]. Schuld, Sweke, and Meyer characterize the resulting model class as a partial Fourier series whose accessible frequencies are determined by the encoding gates and upload schedule [@Schuld2021DataEncoding]. Jerbi et al. show how re-uploading fits into the broader linear-model-in-Hilbert-space picture [@Jerbi2023BeyondKernelMethods].

The direct implication for QAtelier is that a spectrum/Fourier-matched classical control is mandatory. “The PQC is nonlinear” is not a sufficient mechanism claim. The experiment must determine whether any observed effect is caused by accessible frequency support, coefficient constraints, entanglement, optimization, or noise. Sweke et al. give the most direct recent dequantization test: random Fourier features can efficiently reproduce the analyzed variational-QML regression model under identifiable conditions, but not generically [@Sweke2025RFFDequantization].

### Trainability, effective dimension, and generalization

McClean et al. establish the barren-plateau failure mode for sufficiently expressive random parameterized circuits [@McClean2018BarrenPlateaus]. Cerezo et al. show that gradient concentration depends on cost locality and depth, with local costs potentially more trainable in shallow regimes [@Cerezo2021CostFunctionPlateaus]. Wang et al. establish a distinct noise-induced barren-plateau mechanism under local-noise and depth-scaling assumptions [@Wang2021NoiseInducedBarrenPlateaus]. These results motivate measuring gradient norms and variances rather than assuming that a shallow or ideal-simulator circuit is trainable on hardware.

Abbas et al. introduce a Fisher-information effective-dimension diagnostic and report QNN/classical-network comparisons with hardware verification [@Abbas2021PowerQNN]. Caro et al. derive few-data generalization bounds in terms of trainable gates [@Caro2022GeneralizationFewData], while Gil-Fuster et al. show that QNNs can fit random labels in their studied settings, challenging complexity-only uniform explanations of generalization [@GilFuster2024RethinkingGeneralization]. Together these sources support a preregistered low-data protocol with permutation controls, but they do not predict that QAtelier will generalize well.

### Classical controls and contemporary QML

Stoudenmire and Schwab establish matrix-product-state/tensor-train classifiers as supervised-learning models with an induced structural bias [@Stoudenmire2016TensorNetworks]. Liu and Zhang show why tensor-network contraction and classical simulation should be treated as explicit resource controls when interpreting circuit difficulty [@Liu2023ClassicalCircuitSimulation]. Yamasaki et al. provide a separate theoretical quantum random-feature speedup claim under specific algorithmic assumptions [@Yamasaki2020OptimizedRandomFeatures]. These sources support QAtelier's MPS, tensor-network, and RFF controls; they also make clear that a quantum circuit's difficult simulation is not automatically a useful predictive advantage.

Recent conference work remains directly relevant. Wang et al. find that deep, narrow data-reuploading models can lose predictive performance on high-dimensional data in their studied settings [@Wang2025DeepDataReuploading]. Gil-Fuster et al. formalize the relationship between trainability and dequantization and construct variational models that are intended to satisfy both properties under stated assumptions [@GilFuster2025TrainabilityDequantization]. These works reinforce that QAtelier must measure predictive performance, trainability, and classical simulability as separate axes.

## Novelty overlap table

| Proposed QAtelier element | Prior overlap | Audit judgment | Required positioning |
|---|---|---|---|
| PQC head after a frozen foundation representation | Kim et al.; the 2026 energy follow-up | Directly anticipated | Call it a controlled reproduction/extension, not a new architecture. |
| Quantum adapter in a foundation-model projection layer | Cayley-adapter preprint | Very close conceptual overlap | Differentiate by task, representation-matched controls, mechanism diagnostics, and preregistered claims; inspect the full preprint before any “first” wording. |
| Cross-feature PQC adapter families | QCHFT | Direct method overlap | Treat QCHFT families as related baselines/competitors; do not claim contraction-based adapter novelty. |
| Quantum-inspired tensor/high-rank adaptation | QuanTA | Neighboring classical method | Include as a classical quantum-inspired control where feasible; never count it as physical quantum evidence. |
| Data re-uploading | Pérez-Salinas; Schuld et al.; Jerbi et al. | Established | Novelty can only be in the controlled foundation-representation protocol and mechanism test. |
| Quantum-kernel/feature-space explanation | Schuld & Killoran; Havlíček; Huang; Kübler | Established | Use established theory to frame diagnostics; do not claim a new kernel principle. |
| Kernel flattening/classical approximation audit | Slattery et al.; Sweke et al. | Established direction | Extend the audit to QAtelier representations and trained heads; call the result an empirical extension. |
| MPS/tensor-network classical control | Stoudenmire & Schwab; Liu & Zhang | Established control family | Match feature input, training data, parameter budget, and resource accounting. |
| Effective dimension and Fisher diagnostics | Abbas et al. | Established diagnostic | Apply it to frozen foundation representations and connect it to predictive results, without treating it as proof of advantage. |
| Low-data and OOD evaluation | Caro et al.; Gil-Fuster et al. | Established motivation, not the same protocol | Predeclare learning curves, OOD splits, permutation controls, and held-out analysis. |
| Interaction-order and alignment benchmark | No directly verified source in this audit combines it with the above adapter protocol | Candidate methodological contribution | Do not claim novelty until a broader database search and full-text comparison are completed. |
| Cross-execution ideal/noisy/IBM/Helios-1E validation | Hardware precedents exist, but the exact current policy is IBM physical plus Quantinuum Helios-1E emulator only | Candidate protocol contribution | Describe the execution ladder exactly; never call the current phase a two-physical-QPU study. |

## Provisional novelty statement

The defensible provisional position is:

> QAtelier is a proposed controlled evaluation protocol for quantum adapters on frozen foundation-model representations. Its candidate contribution is not a new PQC, a generic quantum fine-tuning claim, or quantum advantage. It is the combination of representation-matched classical controls, a required spectrum/Fourier surrogate, MPS/tensor controls, controlled interaction-order/alignment/entanglement experiments, low-data/OOD evaluation, and a preregistered simulator-to-hardware validation ladder.

This is a protocol-level novelty hypothesis, not a verified “first” claim. The targeted audit found no included primary source that combines all of those elements in one study, but the search was not exhaustive and the 2026 adapter papers are recent. Before manuscript submission, rerun the search across ACL Anthology, OpenAlex/Crossref, Semantic Scholar, arXiv, IEEE Xplore, ACM Digital Library, and the ICLR/ICML/NeurIPS proceedings, and compare the full texts of any newly found adapter papers.

## Preregistration consequences

1. The primary target remains C2: evidence for a distinct useful inductive bias. C1, C3, and C4 must be earned separately; “quantum advantage” is prohibited without the project's C4 criteria.
2. The primary quantum head must use the same frozen representation, train-only compressor, examples, split manifests, seed sets, and model-selection budget as every classical head.
3. Required controls are logistic/linear, strong RBF and polynomial kernels, parameter-matched MLP, RFF, finite RBF network, low-rank/bilinear model, MPS/tensor network, and a spectrum/Fourier-matched surrogate where computationally practical.
4. Mechanism claims require coordinated evidence from interaction-order, entanglement, alignment/rotation, Fourier support, kernel alignment/effective rank, and gradient diagnostics.
5. Hardware is validation only after candidate freeze. IBM physical execution and Quantinuum Helios-1E emulator execution must be reported as different execution regimes; physical Quantinuum execution is excluded by the current project policy.
6. Any negative result is a valid outcome and must be preserved. A classical surrogate that matches the PQC is evidence about the mechanism, not a failed experiment.

## Open verification items

- Read the complete 2026 Cayley and QCHFT papers before finalizing exactly matched baselines and any manuscript comparison.
- Record paper-version identifiers in any future reproduction manifest; early-access and arXiv versions may change.
- Verify all primary-task datasets, split procedures, and hyperparameter-selection rules directly from the source papers before implementing S0.
- Do not use the current audit as a substitute for a final systematic-review search at manuscript freeze.
