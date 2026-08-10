# Workstream E progress

## 2026-08-10 — initial executable simulator

- Implemented a NumPy-only, dependency-lazy statevector simulator under
  `simulation/simulator.py`.
- Preserved the existing adapter contract as `R` serialized data-encoding
  stages followed by `L` trainable blocks; this interpretation is serialized
  with every circuit schedule.
- Defined deterministic parameter names/order, CNOT orientation, qubit/bit
  ordering, Pauli expectation readout, and finite-shot basis rotations.
- Added QIA-P/L/X/A schedules and deterministic disjoint two-qubit round
  partitioning with scheduled depth, while retaining the adapter-declared
  depth for audit comparison.
- Added JSON-compatible schedule and result serialization plus deterministic
  parameter initialization.
- Added an optional Qiskit Aer execution path that is imported only when
  requested; it never contacts cloud providers.
- Added core tests that run without quantum SDKs and an Aer cross-validation
  test that skips when Aer is not installed.
- Verification: focused simulator tests pass (`8 passed`, including Aer on the
  current environment); the complete QAtelier test directory passes (`42
  passed, 7 subtests passed`); Ruff and bytecode compilation pass.
- A full-repository pytest run was attempted in the existing dirty
  multi-workstream checkout. It encountered three unrelated failures and then
  a `pyarrow` segmentation fault in an existing foundation dataset test; no
  Workstream E test failed. The unrelated changes are intentionally not part
  of this workstream commit.

No production Atelier code, `quantum_adapter.py`, or central QAtelier files
were changed by this workstream.
