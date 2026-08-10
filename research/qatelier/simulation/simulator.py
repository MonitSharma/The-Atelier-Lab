"""A small, dependency-lazy statevector simulator for QAtelier.

The simulator is deliberately implemented with NumPy only.  Qiskit Aer is
loaded only by :func:`simulate_with_aer`, so importing or testing this module
does not require a quantum SDK, a provider account, or cloud credentials.

Schedule contract
-----------------
The existing :class:`~research.qatelier.quantum_adapter.QuantumAdapterConfig`
has two independent counts.  To preserve that scaffold contract exactly, this
module interprets a circuit as::

    E_0, E_1, ..., E_(R-1), B_0, B_1, ..., B_(L-1)

where each ``E`` is an encoding stage and each ``B`` is a trainable block.  An
encoding stage applies the configured data rotations (default ``RY(z_i)`` then
``RZ(z_i)``) to every qubit.  A trainable block applies the configured
trainable rotations to every qubit and then applies the configured CNOT
entangling schedule.  ``L`` is therefore *not* silently multiplied by ``R``.
This is the migration-safe interpretation of the current adapter's resource
formula and is recorded in the serialized schedule.

Parameter ordering
------------------
The flattened parameter vector is deterministic and is exposed by
:class:`ParameterLayout`:

1. ``encoding.scale[i]`` for ``i = 0..q-1`` when
   ``encoding.trainable_scale`` is enabled;
2. ``layer[l].qubit[i].ROT`` in lexicographic ``(l, i, ROT)`` order for each
   configured trainable rotation;
3. ``readout.weight[j]`` for each observable when trainable readout weights
   are enabled;
4. ``readout.bias`` when the shared readout bias is enabled.

Trainable encoding scales are shared across all ``R`` uploads and multiply
the corresponding feature before every data rotation.  The readout is an
elementwise affine map, ``y_j = w_j e_j + b``, with unit weights and zero bias
when those options are not trainable.  This preserves one result per
observable and makes the one-bias parameter count in the existing contract
unambiguous.

Gate and bit-order conventions
------------------------------
The entangling operation is a CNOT from the lower-index qubit to the
higher-index qubit.  Qubit zero is the least-significant state-vector bit,
matching Qiskit's little-endian convention.  Measurement strings are printed
most-significant bit first (``q_(q-1)...q_0``), matching Aer count keys.

``QIA-P`` has no CNOTs, ``QIA-L`` uses adjacent pairs, ``QIA-X`` uses all
non-adjacent pairs, and ``QIA-A`` uses the complete graph.  Pairs are first
returned in the adapter's lexicographic order and then deterministically
partitioned into greedy edge-colour rounds.  The round count, scheduled depth,
and the adapter's declared depth are all retained in :class:`ScheduleResources`.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from ..quantum_adapter import (
    EncodingSpec,
    QuantumAdapterConfig,
    ReadoutSpec,
    entangling_pairs,
)


class OptionalSimulatorDependencyError(ImportError):
    """Raised when an optional simulator backend is requested but unavailable."""


_PAULI_RE = re.compile(r"^(?P<pauli>[IXYZ])(?:\[(?P<bracket>\d+)\]|(?P<plain>\d+))$")
_ROTATIONS = frozenset({"RX", "RY", "RZ"})


def _json_dumps(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _coerce_parameters(parameters: Sequence[float] | np.ndarray, expected: int) -> np.ndarray:
    values = np.asarray(parameters, dtype=float)
    if values.ndim != 1:
        raise ValueError("parameters must be a one-dimensional vector")
    if values.size != expected:
        raise ValueError(f"expected {expected} parameters, received {values.size}")
    if not np.all(np.isfinite(values)):
        raise ValueError("parameters must contain only finite values")
    return values.copy()


def _coerce_features(features: Sequence[float] | np.ndarray, q: int) -> np.ndarray:
    values = np.asarray(features, dtype=float)
    if values.ndim != 1 or values.size != q:
        raise ValueError(f"features must be a one-dimensional vector of length q={q}")
    if not np.all(np.isfinite(values)):
        raise ValueError("features must contain only finite values")
    return values.copy()


def _coerce_shots(shots: int | None) -> int | None:
    if shots is None:
        return None
    if not isinstance(shots, int) or isinstance(shots, bool) or shots < 1:
        raise ValueError("shots must be a positive integer or None")
    return shots


def _coerce_seed(seed: int | None) -> int | None:
    if seed is None:
        return None
    if not isinstance(seed, (int, np.integer)) or isinstance(seed, bool):
        raise ValueError("seed must be an integer or None")
    if int(seed) < 0:
        raise ValueError("seed must be non-negative")
    return int(seed)


@dataclass(frozen=True)
class ParameterLayout:
    """Stable names and indices for a flattened QAtelier parameter vector."""

    names: tuple[str, ...]

    @classmethod
    def from_config(cls, config: QuantumAdapterConfig) -> "ParameterLayout":
        if not isinstance(config, QuantumAdapterConfig):
            raise TypeError("config must be a QuantumAdapterConfig")
        names: list[str] = []
        if config.encoding.trainable_scale:
            names.extend(f"encoding.scale[{qubit}]" for qubit in range(config.q))
        for layer in range(config.L):
            for qubit in range(config.q):
                names.extend(
                    f"layer[{layer}].qubit[{qubit}].{rotation}"
                    for rotation in config.trainable_rotations
                )
        if config.readout.trainable_weights:
            names.extend(
                f"readout.weight[{observable_index}]"
                for observable_index in range(len(config.readout.observables))
            )
        if config.readout.trainable_bias:
            names.append("readout.bias")
        layout = cls(tuple(names))
        expected = config.resources().trainable_parameters
        if layout.size != expected:
            raise AssertionError(
                "parameter layout disagrees with QuantumAdapterConfig resource accounting"
            )
        return layout

    @property
    def size(self) -> int:
        return len(self.names)

    def index(self, name: str) -> int:
        try:
            return self.names.index(name)
        except ValueError as exc:
            raise KeyError(name) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"size": self.size, "names": list(self.names)}


@dataclass(frozen=True)
class LogicalOperation:
    """One operation in the backend-neutral executable schedule."""

    section: str
    operation: str
    upload: int | None = None
    layer: int | None = None
    rotation: str | None = None
    qubit: int | None = None
    control: int | None = None
    target: int | None = None
    two_qubit_round: int | None = None
    parameter: str | None = None
    feature_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "section": self.section,
            "operation": self.operation,
            "upload": self.upload,
            "layer": self.layer,
            "rotation": self.rotation,
            "qubit": self.qubit,
            "control": self.control,
            "target": self.target,
            "two_qubit_round": self.two_qubit_round,
            "parameter": self.parameter,
            "feature_index": self.feature_index,
        }


def partition_two_qubit_rounds(
    pairs: Iterable[tuple[int, int]],
) -> tuple[tuple[tuple[int, int], ...], ...]:
    """Partition pairs into deterministic rounds of disjoint interactions.

    This is a greedy edge-colouring schedule.  It does not claim to minimize
    the number of rounds for every graph, but it is deterministic, executable,
    and makes the depth convention explicit.  The predeclared QIA graphs are
    small and regular, so this conservative schedule is sufficient for the
    simulator and resource audit.
    """

    rounds: list[list[tuple[int, int]]] = []
    used_qubits: list[set[int]] = []
    for left, right in pairs:
        if left == right or left < 0 or right < 0:
            raise ValueError("two-qubit pairs must contain distinct non-negative qubits")
        for round_index, occupied in enumerate(used_qubits):
            if left not in occupied and right not in occupied:
                rounds[round_index].append((left, right))
                occupied.update((left, right))
                break
        else:
            rounds.append([(left, right)])
            used_qubits.append({left, right})
    return tuple(tuple(current_round) for current_round in rounds)


@dataclass(frozen=True)
class ScheduleResources:
    """Logical and executable-depth resource accounting for one schedule."""

    qubits: int
    reuploads: int
    trainable_layers: int
    trainable_parameters: int
    encoding_gates: int
    one_qubit_gates: int
    two_qubit_gates: int
    two_qubit_rounds_per_block: int
    two_qubit_rounds: int
    one_qubit_depth: int
    two_qubit_depth: int
    logical_depth: int
    adapter_declared_depth: int
    observables: int
    max_interaction_degree: int
    long_range_two_qubit_gates: int

    @property
    def total_gates(self) -> int:
        return self.one_qubit_gates + self.two_qubit_gates

    def to_dict(self) -> dict[str, int]:
        return {
            "qubits": self.qubits,
            "reuploads": self.reuploads,
            "trainable_layers": self.trainable_layers,
            "trainable_parameters": self.trainable_parameters,
            "encoding_gates": self.encoding_gates,
            "one_qubit_gates": self.one_qubit_gates,
            "two_qubit_gates": self.two_qubit_gates,
            "two_qubit_rounds_per_block": self.two_qubit_rounds_per_block,
            "two_qubit_rounds": self.two_qubit_rounds,
            "one_qubit_depth": self.one_qubit_depth,
            "two_qubit_depth": self.two_qubit_depth,
            "logical_depth": self.logical_depth,
            "adapter_declared_depth": self.adapter_declared_depth,
            "observables": self.observables,
            "max_interaction_degree": self.max_interaction_degree,
            "long_range_two_qubit_gates": self.long_range_two_qubit_gates,
            "total_gates": self.total_gates,
        }


@dataclass(frozen=True)
class CircuitSchedule:
    """Materialized QAtelier operation schedule and its resource ledger."""

    config: QuantumAdapterConfig
    operations: tuple[LogicalOperation, ...]
    entangling_rounds: tuple[tuple[tuple[int, int], ...], ...]
    parameter_layout: ParameterLayout
    resources: ScheduleResources

    @classmethod
    def from_config(cls, config: QuantumAdapterConfig) -> "CircuitSchedule":
        if not isinstance(config, QuantumAdapterConfig):
            raise TypeError("config must be a QuantumAdapterConfig")

        pairs = entangling_pairs(config.q, config.family)
        rounds = partition_two_qubit_rounds(pairs)
        layout = ParameterLayout.from_config(config)
        operations: list[LogicalOperation] = []

        for upload in range(config.R):
            for rotation in config.encoding.rotations:
                for qubit in range(config.q):
                    parameter = (
                        f"encoding.scale[{qubit}]" if config.encoding.trainable_scale else None
                    )
                    operations.append(
                        LogicalOperation(
                            section="encoding",
                            operation=rotation,
                            upload=upload,
                            rotation=rotation,
                            qubit=qubit,
                            parameter=parameter,
                            feature_index=qubit,
                        )
                    )

        for layer in range(config.L):
            for rotation in config.trainable_rotations:
                for qubit in range(config.q):
                    operations.append(
                        LogicalOperation(
                            section="trainable",
                            operation=rotation,
                            layer=layer,
                            rotation=rotation,
                            qubit=qubit,
                            parameter=f"layer[{layer}].qubit[{qubit}].{rotation}",
                        )
                    )
            for round_index, current_round in enumerate(rounds):
                for control, target in current_round:
                    operations.append(
                        LogicalOperation(
                            section="entangling",
                            operation="CNOT",
                            layer=layer,
                            control=control,
                            target=target,
                            two_qubit_round=round_index,
                        )
                    )

        degrees = [0] * config.q
        for control, target in pairs:
            degrees[control] += 1
            degrees[target] += 1
        resources_from_adapter = config.resources()
        one_qubit_depth = config.R * config.encoding.depth + config.L * len(
            config.trainable_rotations
        )
        two_qubit_rounds = config.L * len(rounds)
        resources = ScheduleResources(
            qubits=config.q,
            reuploads=config.R,
            trainable_layers=config.L,
            trainable_parameters=layout.size,
            encoding_gates=resources_from_adapter.encoding_gates,
            one_qubit_gates=resources_from_adapter.one_qubit_gates,
            two_qubit_gates=resources_from_adapter.two_qubit_gates,
            two_qubit_rounds_per_block=len(rounds),
            two_qubit_rounds=two_qubit_rounds,
            one_qubit_depth=one_qubit_depth,
            two_qubit_depth=two_qubit_rounds,
            logical_depth=one_qubit_depth + two_qubit_rounds,
            adapter_declared_depth=resources_from_adapter.logical_depth,
            observables=resources_from_adapter.observables,
            max_interaction_degree=max(degrees, default=0),
            long_range_two_qubit_gates=sum(
                int(target - control > 1) for control, target in pairs
            ) * config.L,
        )
        return cls(config, tuple(operations), rounds, layout, resources)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CircuitSchedule":
        """Rebuild a schedule from its JSON-compatible representation."""

        try:
            config_data = payload["config"]
            encoding_data = config_data["encoding"]
            readout_data = config_data["readout"]
            config = QuantumAdapterConfig(
                q=int(config_data["q"]),
                R=int(config_data["R"]),
                L=int(config_data["L"]),
                encoding=EncodingSpec(
                    name=encoding_data["name"],
                    rotations=tuple(encoding_data["rotations"]),
                    trainable_scale=bool(encoding_data["trainable_scale"]),
                ),
                readout=ReadoutSpec(
                    observables=tuple(readout_data["observables"]),
                    trainable_weights=bool(readout_data["trainable_weights"]),
                    trainable_bias=bool(readout_data["trainable_bias"]),
                ),
                family=config_data["family"],
                trainable_rotations=tuple(config_data["trainable_rotations"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid serialized CircuitSchedule payload") from exc
        schedule = cls.from_config(config)
        serialized_layout = payload.get("parameter_layout")
        if serialized_layout is not None and tuple(serialized_layout["names"]) != schedule.parameter_layout.names:
            raise ValueError("serialized parameter layout does not match config")
        return schedule

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "semantics": {
                "stage_order": "all_R_encoding_stages_then_all_L_trainable_blocks",
                "entangler": "CNOT_lower_index_control_to_higher_index_target",
                "qubit_zero": "least_significant_statevector_bit",
                "measurement_string": "q_(q-1)_through_q_0",
            },
            "config": self.config.to_dict(),
            "parameter_layout": self.parameter_layout.to_dict(),
            "entangling_rounds": [
                [list(pair) for pair in current_round] for current_round in self.entangling_rounds
            ],
            "operations": [operation.to_dict() for operation in self.operations],
            "resources": self.resources.to_dict(),
        }

    def to_json(self) -> str:
        return _json_dumps(self.to_dict())

    @classmethod
    def from_json(cls, serialized: str) -> "CircuitSchedule":
        return cls.from_dict(json.loads(serialized))


@dataclass(frozen=True)
class SimulationResult:
    """Serializable exact or finite-shot expectation-readout result."""

    config: QuantumAdapterConfig
    features: np.ndarray
    parameters: np.ndarray
    raw_expectations: np.ndarray
    expectations: np.ndarray
    shots: int | None
    seed: int | None
    counts: tuple[dict[str, int], ...] | None
    resources: ScheduleResources
    statevector: np.ndarray | None = None

    @property
    def values(self) -> np.ndarray:
        """Alias for the readout values returned to an adapter consumer."""

        return self.expectations

    @property
    def observable_order(self) -> tuple[str, ...]:
        return self.config.readout.observables

    def to_dict(self, *, include_statevector: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": 1,
            "config": self.config.to_dict(),
            "observable_order": list(self.observable_order),
            "features": self.features.tolist(),
            "parameters": self.parameters.tolist(),
            "raw_expectations": self.raw_expectations.tolist(),
            "expectations": self.expectations.tolist(),
            "shots": self.shots,
            "seed": self.seed,
            "counts": [dict(sorted(item.items())) for item in self.counts]
            if self.counts is not None
            else None,
            "resources": self.resources.to_dict(),
        }
        if include_statevector:
            payload["statevector"] = (
                {
                    "real": np.asarray(self.statevector).real.tolist(),
                    "imag": np.asarray(self.statevector).imag.tolist(),
                }
                if self.statevector is not None
                else None
            )
        return payload

    def to_json(self, *, include_statevector: bool = True) -> str:
        return _json_dumps(self.to_dict(include_statevector=include_statevector))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SimulationResult":
        config_data = payload["config"]
        config = QuantumAdapterConfig(
            q=int(config_data["q"]),
            R=int(config_data["R"]),
            L=int(config_data["L"]),
            encoding=EncodingSpec(**config_data["encoding"]),
            readout=ReadoutSpec(
                observables=tuple(config_data["readout"]["observables"]),
                trainable_weights=bool(config_data["readout"]["trainable_weights"]),
                trainable_bias=bool(config_data["readout"]["trainable_bias"]),
            ),
            family=config_data["family"],
            trainable_rotations=tuple(config_data["trainable_rotations"]),
        )
        serialized_state = payload.get("statevector")
        statevector = None
        if serialized_state is not None:
            statevector = np.asarray(serialized_state["real"], dtype=float) + 1j * np.asarray(
                serialized_state["imag"], dtype=float
            )
        counts_payload = payload.get("counts")
        counts = (
            tuple({str(key): int(value) for key, value in item.items()} for item in counts_payload)
            if counts_payload is not None
            else None
        )
        return cls(
            config=config,
            features=np.asarray(payload["features"], dtype=float),
            parameters=np.asarray(payload["parameters"], dtype=float),
            raw_expectations=np.asarray(payload["raw_expectations"], dtype=float),
            expectations=np.asarray(payload["expectations"], dtype=float),
            shots=payload.get("shots"),
            seed=payload.get("seed"),
            counts=counts,
            resources=CircuitSchedule.from_config(config).resources,
            statevector=statevector,
        )

    @classmethod
    def from_json(cls, serialized: str) -> "SimulationResult":
        return cls.from_dict(json.loads(serialized))


def _single_qubit_matrix(rotation: str, angle: float) -> np.ndarray:
    half = angle / 2.0
    cosine = np.cos(half)
    sine = np.sin(half)
    if rotation == "RX":
        return np.array([[cosine, -1j * sine], [-1j * sine, cosine]], dtype=complex)
    if rotation == "RY":
        return np.array([[cosine, -sine], [sine, cosine]], dtype=complex)
    if rotation == "RZ":
        return np.array(
            [[np.exp(-1j * half), 0.0], [0.0, np.exp(1j * half)]],
            dtype=complex,
        )
    raise ValueError(f"unsupported rotation {rotation!r}")


def _apply_single_qubit(state: np.ndarray, matrix: np.ndarray, qubit: int) -> np.ndarray:
    result = state.copy()
    stride = 1 << qubit
    block = stride << 1
    for base in range(0, state.size, block):
        for offset in range(stride):
            zero = base + offset
            one = zero + stride
            amplitude_zero = state[zero]
            amplitude_one = state[one]
            result[zero] = matrix[0, 0] * amplitude_zero + matrix[0, 1] * amplitude_one
            result[one] = matrix[1, 0] * amplitude_zero + matrix[1, 1] * amplitude_one
    return result


def _apply_cnot(state: np.ndarray, control: int, target: int) -> np.ndarray:
    result = state.copy()
    control_mask = 1 << control
    target_mask = 1 << target
    for index in range(state.size):
        if index & control_mask and not index & target_mask:
            partner = index | target_mask
            result[index] = state[partner]
            result[partner] = state[index]
    return result


def _observable_parts(observable: str, q: int) -> tuple[str, int]:
    match = _PAULI_RE.fullmatch(observable)
    if match is None:
        raise ValueError(f"invalid observable {observable!r}")
    qubit = int(match.group("bracket") or match.group("plain"))
    if qubit >= q:
        raise ValueError(f"observable {observable!r} addresses a qubit outside q={q}")
    return match.group("pauli"), qubit


def _pauli_expectation(state: np.ndarray, pauli: str, qubit: int) -> float:
    if pauli == "Z":
        indices = np.arange(state.size)
        signs = 1.0 - 2.0 * ((indices >> qubit) & 1)
        return float(np.real(np.sum(np.abs(state) ** 2 * signs)))
    stride = 1 << qubit
    block = stride << 1
    total = 0.0 + 0.0j
    for base in range(0, state.size, block):
        for offset in range(stride):
            zero = base + offset
            one = zero + stride
            if pauli == "X":
                total += np.conj(state[zero]) * state[one] + np.conj(state[one]) * state[zero]
            elif pauli == "Y":
                total += (
                    -1j * np.conj(state[zero]) * state[one]
                    + 1j * np.conj(state[one]) * state[zero]
                )
            else:
                raise ValueError(f"unsupported Pauli {pauli!r}")
    return float(np.real(total))


def _measurement_state(state: np.ndarray, pauli: str, qubit: int) -> np.ndarray:
    if pauli == "Z":
        return state
    if pauli == "X":
        hadamard = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / np.sqrt(2.0)
        return _apply_single_qubit(state, hadamard, qubit)
    if pauli == "Y":
        s_dagger = np.array([[1.0, 0.0], [0.0, -1j]], dtype=complex)
        hadamard = np.array([[1.0, 1.0], [1.0, -1.0]], dtype=complex) / np.sqrt(2.0)
        return _apply_single_qubit(_apply_single_qubit(state, s_dagger, qubit), hadamard, qubit)
    raise ValueError(f"unsupported Pauli {pauli!r}")


def _sample_counts(
    state: np.ndarray,
    q: int,
    shots: int,
    rng: np.random.Generator,
) -> dict[str, int]:
    probabilities = np.abs(state) ** 2
    probabilities = probabilities / probabilities.sum()
    sampled = rng.choice(state.size, size=shots, p=probabilities)
    histogram = np.bincount(sampled, minlength=state.size)
    return {
        format(index, f"0{q}b"): int(count)
        for index, count in enumerate(histogram)
        if count
    }


def _expectation_from_counts(counts: Mapping[str, int], pauli: str, qubit: int, q: int) -> float:
    shots = sum(counts.values())
    if shots < 1:
        raise ValueError("counts must contain at least one shot")
    total = 0
    for bitstring, count in counts.items():
        normalized = bitstring.replace(" ", "")
        if len(normalized) != q or any(bit not in "01" for bit in normalized):
            raise ValueError("count bitstrings must be q-bit binary strings")
        index = int(normalized, 2)
        eigenvalue = 1 if pauli == "X" else 1
        if pauli in {"Z", "X", "Y"}:
            eigenvalue = 1 - 2 * ((index >> qubit) & 1)
        total += int(count) * eigenvalue
    return float(total / shots)


class PQCStatevectorSimulator:
    """NumPy-only executable simulator for one QAtelier schedule."""

    def __init__(self, config: QuantumAdapterConfig | CircuitSchedule):
        self.schedule = (
            config if isinstance(config, CircuitSchedule) else CircuitSchedule.from_config(config)
        )

    @property
    def config(self) -> QuantumAdapterConfig:
        return self.schedule.config

    @property
    def parameter_layout(self) -> ParameterLayout:
        return self.schedule.parameter_layout

    def initialize_parameters(self, seed: int = 0, scale: float = 0.1) -> np.ndarray:
        return initialize_parameters(self.config, seed=seed, scale=scale)

    def _statevector(self, features: np.ndarray, parameters: np.ndarray) -> np.ndarray:
        q = self.config.q
        state = np.zeros(1 << q, dtype=complex)
        state[0] = 1.0
        scales = np.ones(q, dtype=float)
        if self.config.encoding.trainable_scale:
            scales = np.asarray(
                [parameters[self.parameter_layout.index(f"encoding.scale[{qubit}]")] for qubit in range(q)]
            )

        for operation in self.schedule.operations:
            if operation.operation == "CNOT":
                state = _apply_cnot(state, int(operation.control), int(operation.target))
                continue
            if operation.section == "encoding":
                angle = features[int(operation.feature_index)] * scales[int(operation.qubit)]
            else:
                angle = parameters[self.parameter_layout.index(str(operation.parameter))]
            state = _apply_single_qubit(
                state,
                _single_qubit_matrix(str(operation.rotation), float(angle)),
                int(operation.qubit),
            )
        return state

    def run(
        self,
        features: Sequence[float] | np.ndarray,
        parameters: Sequence[float] | np.ndarray,
        *,
        shots: int | None = None,
        seed: int | None = None,
        return_statevector: bool = False,
    ) -> SimulationResult:
        values = _coerce_features(features, self.config.q)
        theta = _coerce_parameters(parameters, self.parameter_layout.size)
        checked_shots = _coerce_shots(shots)
        checked_seed = _coerce_seed(seed)
        if checked_shots is None and checked_seed is not None:
            raise ValueError("seed is only meaningful for finite-shot execution")
        state = self._statevector(values, theta)
        raw: list[float] = []
        counts: list[dict[str, int]] | None = [] if checked_shots is not None else None
        rng = np.random.default_rng(checked_seed) if checked_shots is not None else None
        for observable in self.config.readout.observables:
            pauli, qubit = _observable_parts(observable, self.config.q)
            if checked_shots is None:
                raw.append(_pauli_expectation(state, pauli, qubit))
            else:
                measured = _measurement_state(state, pauli, qubit)
                current_counts = _sample_counts(measured, self.config.q, checked_shots, rng)
                counts.append(current_counts)
                raw.append(_expectation_from_counts(current_counts, pauli, qubit, self.config.q))

        raw_array = np.asarray(raw, dtype=float)
        weights = np.ones_like(raw_array)
        if self.config.readout.trainable_weights:
            weights = np.asarray(
                [
                    theta[self.parameter_layout.index(f"readout.weight[{index}]")]
                    for index in range(len(raw_array))
                ],
                dtype=float,
            )
        bias = 0.0
        if self.config.readout.trainable_bias:
            bias = float(theta[self.parameter_layout.index("readout.bias")])
        readout = weights * raw_array + bias
        return SimulationResult(
            config=self.config,
            features=values,
            parameters=theta,
            raw_expectations=raw_array,
            expectations=readout,
            shots=checked_shots,
            seed=checked_seed,
            counts=tuple(counts) if counts is not None else None,
            resources=self.schedule.resources,
            statevector=state if return_statevector else None,
        )

    def execute(
        self,
        features: Sequence[float] | np.ndarray,
        parameters: Sequence[float] | np.ndarray,
        *,
        shots: int | None = None,
        seed: int | None = None,
    ) -> np.ndarray:
        """Adapter-compatible convenience method returning readout values."""

        return self.run(features, parameters, shots=shots, seed=seed).expectations


def initialize_parameters(
    config: QuantumAdapterConfig,
    *,
    seed: int = 0,
    scale: float = 0.1,
) -> np.ndarray:
    """Create deterministic parameters in the documented layout.

    Circuit angles and trainable encoding scales are sampled from a centered
    normal distribution with the requested standard deviation.  Readout
    weights are initialized to one and the shared readout bias to zero.  The
    split is intentional: the default readout starts as an identity map while
    circuit parameters still receive a reproducible non-zero initialization.
    """

    if not isinstance(config, QuantumAdapterConfig):
        raise TypeError("config must be a QuantumAdapterConfig")
    if not isinstance(scale, (int, float)) or not np.isfinite(scale) or scale < 0:
        raise ValueError("scale must be a finite non-negative number")
    checked_seed = _coerce_seed(seed)
    rng = np.random.default_rng(checked_seed)
    layout = ParameterLayout.from_config(config)
    values = np.zeros(layout.size, dtype=float)
    for index, name in enumerate(layout.names):
        if name.startswith("readout.weight"):
            values[index] = 1.0
        elif name == "readout.bias":
            values[index] = 0.0
        else:
            values[index] = rng.normal(0.0, float(scale))
    return values


def simulate(
    config: QuantumAdapterConfig,
    features: Sequence[float] | np.ndarray,
    parameters: Sequence[float] | np.ndarray,
    *,
    shots: int | None = None,
    seed: int | None = None,
    return_statevector: bool = False,
) -> SimulationResult:
    """Run exact (``shots=None``) or finite-shot NumPy simulation."""

    return PQCStatevectorSimulator(config).run(
        features,
        parameters,
        shots=shots,
        seed=seed,
        return_statevector=return_statevector,
    )


def simulate_batch(
    config: QuantumAdapterConfig,
    features: Sequence[Sequence[float]] | np.ndarray,
    parameters: Sequence[float] | np.ndarray,
    *,
    shots: int | None = None,
    seed: int | None = None,
) -> np.ndarray:
    """Run the same frozen parameters on a batch and return an ``(n, m)`` array."""

    batch = np.asarray(features, dtype=float)
    if batch.ndim != 2 or batch.shape[1] != config.q:
        raise ValueError(f"features must have shape (n_samples, q={config.q})")
    results = [
        simulate(config, row, parameters, shots=shots, seed=None if seed is None else seed + index)
        for index, row in enumerate(batch)
    ]
    return np.vstack([result.expectations for result in results])


def aer_available() -> bool:
    """Return whether local Qiskit Aer can be imported, without importing it eagerly."""

    try:
        import qiskit  # noqa: F401
        import qiskit_aer  # noqa: F401
    except ImportError:
        return False
    return True


def _require_aer() -> tuple[Any, Any]:
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        raise OptionalSimulatorDependencyError(
            "Qiskit Aer cross-validation requires the optional qiskit-aer dependency"
        ) from exc
    return QuantumCircuit, AerSimulator


def _append_qiskit_schedule(
    circuit: Any,
    schedule: CircuitSchedule,
    features: np.ndarray,
    parameters: np.ndarray,
) -> None:
    layout = schedule.parameter_layout
    scales = np.ones(schedule.config.q, dtype=float)
    if schedule.config.encoding.trainable_scale:
        scales = np.asarray(
            [parameters[layout.index(f"encoding.scale[{qubit}]")] for qubit in range(schedule.config.q)]
        )
    for operation in schedule.operations:
        if operation.operation == "CNOT":
            circuit.cx(int(operation.control), int(operation.target))
            continue
        if operation.section == "encoding":
            angle = features[int(operation.feature_index)] * scales[int(operation.qubit)]
        else:
            angle = parameters[layout.index(str(operation.parameter))]
        qubit = int(operation.qubit)
        if operation.rotation == "RX":
            circuit.rx(float(angle), qubit)
        elif operation.rotation == "RY":
            circuit.ry(float(angle), qubit)
        elif operation.rotation == "RZ":
            circuit.rz(float(angle), qubit)
        else:
            raise ValueError(f"unsupported rotation {operation.rotation!r}")


def _qiskit_measurement_basis(circuit: Any, pauli: str, qubit: int) -> None:
    if pauli == "X":
        circuit.h(qubit)
    elif pauli == "Y":
        circuit.sdg(qubit)
        circuit.h(qubit)
    elif pauli != "Z":
        raise ValueError(f"unsupported Pauli {pauli!r}")


def _counts_expectation_from_aer(
    counts: Mapping[str, int],
    pauli: str,
    qubit: int,
    q: int,
) -> float:
    normalized = {str(key).replace(" ", ""): int(value) for key, value in counts.items()}
    return _expectation_from_counts(normalized, pauli, qubit, q)


def simulate_with_aer(
    config: QuantumAdapterConfig,
    features: Sequence[float] | np.ndarray,
    parameters: Sequence[float] | np.ndarray,
    *,
    shots: int | None = None,
    seed: int | None = None,
    return_statevector: bool = False,
) -> SimulationResult:
    """Cross-check the common schedule with a local Qiskit Aer simulator.

    This function never contacts IBM Quantum or any other provider.  For an
    exact run it retrieves Aer's statevector and uses the same observable
    evaluator as the NumPy implementation.  For finite shots, each observable
    gets its own basis-rotated Aer circuit and count sample.
    """

    QuantumCircuit, AerSimulator = _require_aer()
    schedule = CircuitSchedule.from_config(config)
    values = _coerce_features(features, config.q)
    theta = _coerce_parameters(parameters, schedule.parameter_layout.size)
    checked_shots = _coerce_shots(shots)
    checked_seed = _coerce_seed(seed)
    if checked_shots is None and checked_seed is not None:
        raise ValueError("seed is only meaningful for finite-shot execution")
    backend = AerSimulator(method="statevector")
    statevector: np.ndarray | None = None
    raw: list[float] = []
    counts: list[dict[str, int]] | None = [] if checked_shots is not None else None

    if checked_shots is None:
        circuit = QuantumCircuit(config.q)
        _append_qiskit_schedule(circuit, schedule, values, theta)
        circuit.save_statevector()
        aer_result = backend.run(circuit, seed_simulator=checked_seed).result()
        data = aer_result.data(0)
        statevector = np.asarray(data["statevector"], dtype=complex)
        for observable in config.readout.observables:
            pauli, qubit = _observable_parts(observable, config.q)
            raw.append(_pauli_expectation(statevector, pauli, qubit))
    else:
        for observable_index, observable in enumerate(config.readout.observables):
            pauli, qubit = _observable_parts(observable, config.q)
            circuit = QuantumCircuit(config.q, config.q)
            _append_qiskit_schedule(circuit, schedule, values, theta)
            _qiskit_measurement_basis(circuit, pauli, qubit)
            circuit.measure(range(config.q), range(config.q))
            current_seed = None if checked_seed is None else checked_seed + observable_index
            aer_result = backend.run(
                circuit,
                shots=checked_shots,
                seed_simulator=current_seed,
            ).result()
            current_counts = {
                str(key).replace(" ", ""): int(value)
                for key, value in aer_result.get_counts(0).items()
            }
            counts.append(current_counts)
            raw.append(_counts_expectation_from_aer(current_counts, pauli, qubit, config.q))

    raw_array = np.asarray(raw, dtype=float)
    layout = schedule.parameter_layout
    weights = np.ones_like(raw_array)
    if config.readout.trainable_weights:
        weights = np.asarray(
            [theta[layout.index(f"readout.weight[{index}]")] for index in range(len(raw_array))],
            dtype=float,
        )
    bias = theta[layout.index("readout.bias")] if config.readout.trainable_bias else 0.0
    return SimulationResult(
        config=config,
        features=values,
        parameters=theta,
        raw_expectations=raw_array,
        expectations=weights * raw_array + bias,
        shots=checked_shots,
        seed=checked_seed,
        counts=tuple(counts) if counts is not None else None,
        resources=schedule.resources,
        statevector=statevector if return_statevector else None,
    )


def cross_validate_aer(
    config: QuantumAdapterConfig,
    features: Sequence[float] | np.ndarray,
    parameters: Sequence[float] | np.ndarray,
    *,
    atol: float = 1e-8,
) -> dict[str, Any]:
    """Return an exact NumPy-vs-Aer agreement report for one input."""

    numpy_result = simulate(config, features, parameters)
    aer_result = simulate_with_aer(config, features, parameters)
    error = float(np.max(np.abs(numpy_result.expectations - aer_result.expectations)))
    return {
        "numpy_expectations": numpy_result.expectations.tolist(),
        "aer_expectations": aer_result.expectations.tolist(),
        "max_abs_error": error,
        "atol": atol,
        "passed": bool(error <= atol),
        "schedule": numpy_result.resources.to_dict(),
    }


__all__ = [
    "CircuitSchedule",
    "LogicalOperation",
    "OptionalSimulatorDependencyError",
    "ParameterLayout",
    "PQCStatevectorSimulator",
    "ScheduleResources",
    "SimulationResult",
    "aer_available",
    "cross_validate_aer",
    "initialize_parameters",
    "partition_two_qubit_rounds",
    "simulate",
    "simulate_batch",
    "simulate_with_aer",
]
