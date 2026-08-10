# Workstream E — simulator contract

This directory contains the first executable PQC implementation for QAtelier.
It is intentionally isolated from production Atelier code and imports only
NumPy at module import time. Qiskit Aer is an optional local cross-validation
backend; no IBM or Quantinuum credentials are needed for the simulator or its
tests.

## Exact schedule

The current `QuantumAdapterConfig` is interpreted without changing its
definition:

```text
R encoding stages → L trainable blocks
```

Each encoding stage applies `RY(feature[i])`, then `RZ(feature[i])` to every
qubit. Each trainable block applies the configured `RX`/`RY`/`RZ` parameters to
every qubit, followed by CNOTs for the selected family. The CNOT control is the
lower-index qubit and the target is the higher-index qubit.

The four schedules are:

| Family | Pairs |
| --- | --- |
| QIA-P | no pairs |
| QIA-L | `(0,1), (1,2), ...` |
| QIA-X | every non-adjacent pair |
| QIA-A | every pair `(i,j)` for `i < j` |

Pairs are greedily partitioned into disjoint two-qubit rounds. The schedule
records both gate count and executable round/depth counts. In particular, a
dense QIA-A block is not reported as one two-qubit layer when its gates share
qubits.

## Parameters and readout

`ParameterLayout.names` is the authoritative ordering:

1. `encoding.scale[i]` (only when enabled);
2. `layer[l].qubit[i].ROT`, ordered by layer, qubit, and configured rotation;
3. `readout.weight[j]` (only when enabled);
4. `readout.bias` (only when enabled).

The exact path returns expectation values for the configured observables. The
finite-shot path performs independent basis-rotated measurements per
observable (`Z` computational basis, `X` with `H`, `Y` with `S†` then `H`) and
returns counts plus shot estimates. Readout options apply the elementwise
affine map `y[j] = weight[j] * expectation[j] + bias`, with implicit unit
weights and zero bias when not trainable.

## Example

```python
import numpy as np

from research.qatelier.quantum_adapter import QuantumAdapterConfig
from research.qatelier.simulation import simulate

config = QuantumAdapterConfig(q=2, R=1, L=1, family="QIA-L")
theta = np.zeros(config.resources().trainable_parameters)
exact = simulate(config, np.array([0.2, -0.1]), theta)
shot_based = simulate(config, np.array([0.2, -0.1]), theta, shots=4096, seed=7)
```

For optional local Aer agreement:

```python
from research.qatelier.simulation import cross_validate_aer

report = cross_validate_aer(config, np.array([0.2, -0.1]), theta)
assert report["passed"]
```

The result and schedule objects provide `to_dict()` and stable `to_json()`
serialization. No serialized object contains provider credentials.
