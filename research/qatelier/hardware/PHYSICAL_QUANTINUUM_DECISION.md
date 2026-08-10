# Physical Quantinuum decision

## Current recommendation: DO NOT RECOMMEND PHYSICAL QUANTINUUM VALIDATION

The current QAtelier phase produced no frozen quantum candidate. S0 and S2
quantum heads were near chance and did not exceed the representation-matched
classical controls. There is therefore no scientifically defined circuit panel
whose physical Quantinuum execution could test a surviving effect.

Current evidence:

- IBM: credentials and backend metadata were checked read-only; no physical
  job was submitted because the frozen-candidate gate failed.
- Quantinuum: the exact `Helios-1E` emulator identifier was verified; no
  emulator campaign was submitted because no candidate was frozen.
- Quantinuum physical hardware: **0 jobs submitted by design**.

Estimated physical-device cost: not estimated for submission because there is
no frozen candidate/circuit panel. Any future estimate must be produced by the
official syntax/resource checker and preserved separately from actual charges.

Minimum future physical study, if a new preregistration is approved:

1. freeze candidate architecture, parameters, compressor, samples, shots, and
   observables;
2. run ideal and finite-shot/noisy simulator controls;
3. run the IBM physical pilot if its gate passes;
4. run the exact Helios-1E emulator campaign after syntax/HQC cost approval;
5. reassess whether physical Quantinuum adds scientific value before any human
   authorized physical submission.

The current Codex campaign ends before that decision. The recommendation is
advisory and does not authorize future execution.
