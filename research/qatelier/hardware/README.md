# QAtelier hardware policy

Hardware is validation only. Parameters, compressors, sample IDs, shots, and
circuits must be frozen after simulator and noise gates before any IBM run.

Current provider policy:

- IBM physical execution is permitted only behind the frozen-candidate gate.
- Quantinuum physical execution is disabled by code and configuration.
- Quantinuum execution, if the emulator stage is reached, may target only the
  exact `Helios-1E` emulator identifier.
- Every Quantinuum emulator submission must have an accepted syntax/resource
  cost manifest matching the exact circuit and configuration.

Provider-specific raw results, manifests, cost reports, and decision logs will
live under `ibm/` and `quantinuum/`. No credentials or unredacted provider
responses containing secrets may be committed.
