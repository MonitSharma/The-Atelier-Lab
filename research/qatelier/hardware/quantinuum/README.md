# Quantinuum execution policy

The current QAtelier campaign is emulator-only. The only permitted target is
`Helios-1E`; `H2-2`, `Helios-1`, and every other physical Quantinuum target are
blocked by [`policy.py`](../policy.py).

`cost.py` defines the immutable syntax/resource manifest and human-readable
cost report. Estimates and provider-reported actual charges are separate
fields; an estimate is never overwritten after execution.

`discovery.py` performs a read-only catalogue query and refuses to continue if
the exact `Helios-1E` identifier is not exposed uniquely by the configured
Nexus account.

Before a future emulator campaign can submit, it must preserve an immutable
cost-check artifact containing the exact logical/configuration hashes, backend,
syntax-check result, compiled resource counts, estimated HQC cost, checker
timestamp, and software versions. The estimate must remain distinct from any
provider-reported actual charge.

No Quantinuum job is submitted by the P0 preflight or policy tests.
