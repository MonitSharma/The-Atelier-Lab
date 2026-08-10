"""Backend-neutral quantum-adapter contract for QAtelier.

The module intentionally contains no quantum-framework imports.  It defines
the logical circuit contract that a simulator or hardware runner must honor.
The resource counts are deterministic and deliberately do not include
framework compilation, shots, device calibration, or wall-clock cost.

The accounting convention is:

* ``R`` is the number of angle-encoding stages;
* ``L`` is the number of trainable hardware-efficient blocks;
* each trainable block has one ``RX``, ``RY``, and ``RZ`` per qubit, followed by
  one entangling layer for the selected family;
* stages are serialized and no gate cancellation or fusion is assumed.

This is a logical contract, not an implementation of quantum execution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
import re
from typing import Any, Protocol

import numpy as np


class EntanglementFamily(str, Enum):
    """The four predeclared QAtelier interaction families."""

    QIA_P = "QIA-P"
    QIA_L = "QIA-L"
    QIA_X = "QIA-X"
    QIA_A = "QIA-A"

    @classmethod
    def coerce(cls, value: "EntanglementFamily | str") -> "EntanglementFamily":
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError("entanglement family must be an EntanglementFamily or string")
        normalized = value.strip().upper().replace("_", "-")
        try:
            return cls(normalized)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in cls)
            raise ValueError(f"unknown entanglement family {value!r}; expected one of {allowed}") from exc


_ENCODING_ALIASES = {
    "angle": "angle_ry_rz",
    "angle_ry_rz": "angle_ry_rz",
    "angle-ry-rz": "angle_ry_rz",
    "angle_ry": "angle_ry",
    "angle-ry": "angle_ry",
}
_ALLOWED_ROTATIONS = frozenset({"RX", "RY", "RZ"})


@dataclass(frozen=True)
class EncodingSpec:
    """Immutable description of one data-encoding stage.

    The default is the angle encoding used in the QAtelier design, ``RY(z_i)``
    followed by ``RZ(z_i)`` on each qubit.  ``trainable_scale`` adds one
    trainable scale per encoded feature/qubit; it is false by default so that
    the data map itself is not silently counted as a trainable head.
    """

    name: str = "angle_ry_rz"
    rotations: tuple[str, ...] = ("RY", "RZ")
    trainable_scale: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("encoding name must be a string")
        key = self.name.strip().lower().replace(" ", "_")
        canonical = _ENCODING_ALIASES.get(key)
        if canonical is None:
            allowed = ", ".join(sorted(set(_ENCODING_ALIASES.values())))
            raise ValueError(f"unknown encoding {self.name!r}; expected one of {allowed}")

        rotations = tuple(rotation.strip().upper() for rotation in self.rotations)
        if not rotations:
            raise ValueError("encoding must contain at least one rotation")
        if any(rotation not in _ALLOWED_ROTATIONS for rotation in rotations):
            raise ValueError("encoding rotations must be chosen from RX, RY, and RZ")
        if canonical == "angle_ry_rz" and rotations != ("RY", "RZ"):
            raise ValueError("angle_ry_rz encoding must use rotations ('RY', 'RZ')")
        if canonical == "angle_ry" and rotations != ("RY",):
            raise ValueError("angle_ry encoding must use rotation ('RY',)")
        if not isinstance(self.trainable_scale, bool):
            raise TypeError("trainable_scale must be a boolean")

        object.__setattr__(self, "name", canonical)
        object.__setattr__(self, "rotations", rotations)

    @property
    def depth(self) -> int:
        """Logical depth of one encoding stage under the no-fusion convention."""

        return len(self.rotations)


_PAULI_OBSERVABLE = re.compile(r"^[IXYZ](?:\[?\d+\]?)$")


@dataclass(frozen=True)
class ReadoutSpec:
    """Immutable expectation-value readout description.

    Observables use compact labels such as ``Z0`` or ``X[2]``.  Each label
    denotes one measured Pauli observable.  Optional linear readout weights
    and bias are included in the trainable parameter count when enabled.
    """

    observables: tuple[str, ...] = ("Z0",)
    trainable_weights: bool = False
    trainable_bias: bool = False

    def __post_init__(self) -> None:
        observables = tuple(observable.strip().upper() for observable in self.observables)
        if not observables:
            raise ValueError("readout must declare at least one observable")
        for observable in observables:
            if not _PAULI_OBSERVABLE.fullmatch(observable):
                raise ValueError(
                    f"invalid observable {observable!r}; use labels such as 'Z0' or 'X[2]'"
                )
        if not isinstance(self.trainable_weights, bool):
            raise TypeError("trainable_weights must be a boolean")
        if not isinstance(self.trainable_bias, bool):
            raise TypeError("trainable_bias must be a boolean")
        object.__setattr__(self, "observables", observables)

    def trainable_parameter_count(self) -> int:
        """Return parameters belonging to the classical readout map."""

        return len(self.observables) * int(self.trainable_weights) + int(self.trainable_bias)


@dataclass(frozen=True)
class LogicalResources:
    """Deterministic logical resource accounting for a circuit specification."""

    trainable_parameters: int
    encoding_gates: int
    one_qubit_gates: int
    two_qubit_gates: int
    logical_depth: int
    observables: int

    @property
    def total_gates(self) -> int:
        return self.one_qubit_gates + self.two_qubit_gates

    def to_dict(self) -> dict[str, int]:
        return {
            "trainable_parameters": self.trainable_parameters,
            "encoding_gates": self.encoding_gates,
            "one_qubit_gates": self.one_qubit_gates,
            "two_qubit_gates": self.two_qubit_gates,
            "logical_depth": self.logical_depth,
            "observables": self.observables,
        }


def entangling_pairs(q: int, family: EntanglementFamily | str) -> tuple[tuple[int, int], ...]:
    """Return the deterministic logical two-qubit schedule for ``family``.

    QIA-L is a line, QIA-X contains all non-neighbor pairs on that line, and
    QIA-A is the complete graph.  Pairs are returned in lexicographic order.
    """

    if not isinstance(q, int) or isinstance(q, bool) or q < 1:
        raise ValueError("q must be a positive integer")
    selected = EntanglementFamily.coerce(family)
    all_pairs = tuple((left, right) for left in range(q) for right in range(left + 1, q))
    if selected is EntanglementFamily.QIA_P:
        return ()
    if selected is EntanglementFamily.QIA_L:
        return tuple((index, index + 1) for index in range(q - 1))
    if selected is EntanglementFamily.QIA_X:
        return tuple(pair for pair in all_pairs if pair[1] - pair[0] > 1)
    return all_pairs


@dataclass(frozen=True)
class QuantumAdapterConfig:
    """Immutable logical configuration for a QAtelier quantum head.

    ``R`` and ``L`` are retained as explicit field names because they are the
    symbols used in the research contract.  The readable aliases
    :attr:`reupload_count` and :attr:`trainable_block_count` are available to
    callers that do not use the notation from the plan.
    """

    q: int
    R: int
    L: int
    encoding: EncodingSpec = field(default_factory=EncodingSpec)
    readout: ReadoutSpec = field(default_factory=ReadoutSpec)
    family: EntanglementFamily | str = EntanglementFamily.QIA_P
    trainable_rotations: tuple[str, ...] = ("RX", "RY", "RZ")

    def __post_init__(self) -> None:
        for name, value in (("q", self.q), ("R", self.R), ("L", self.L)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.encoding, EncodingSpec):
            raise TypeError("encoding must be an EncodingSpec")
        if not isinstance(self.readout, ReadoutSpec):
            raise TypeError("readout must be a ReadoutSpec")
        rotations = tuple(rotation.strip().upper() for rotation in self.trainable_rotations)
        if not rotations:
            raise ValueError("trainable_rotations must contain at least one rotation")
        if any(rotation not in _ALLOWED_ROTATIONS for rotation in rotations):
            raise ValueError("trainable_rotations must be chosen from RX, RY, and RZ")
        for observable in self.readout.observables:
            index_match = re.search(r"\d+", observable)
            if index_match is not None and int(index_match.group()) >= self.q:
                raise ValueError(f"observable {observable!r} addresses a qubit outside q={self.q}")

        object.__setattr__(self, "family", EntanglementFamily.coerce(self.family))
        object.__setattr__(self, "trainable_rotations", rotations)

    @property
    def reupload_count(self) -> int:
        return self.R

    @property
    def trainable_block_count(self) -> int:
        return self.L

    @property
    def entangling_pairs(self) -> tuple[tuple[int, int], ...]:
        return entangling_pairs(self.q, self.family)

    def resources(self) -> LogicalResources:
        """Compute stable logical resources without compiling or executing."""

        encoding_gates = self.R * self.q * len(self.encoding.rotations)
        trainable_one_qubit_gates = self.L * self.q * len(self.trainable_rotations)
        two_qubit_gates = self.L * len(self.entangling_pairs)
        trainable_parameters = (
            self.L * self.q * len(self.trainable_rotations)
            + self.q * int(self.encoding.trainable_scale)
            + self.readout.trainable_parameter_count()
        )
        block_depth = len(self.trainable_rotations) + int(bool(self.entangling_pairs))
        logical_depth = self.R * self.encoding.depth + self.L * block_depth
        return LogicalResources(
            trainable_parameters=trainable_parameters,
            encoding_gates=encoding_gates,
            one_qubit_gates=encoding_gates + trainable_one_qubit_gates,
            two_qubit_gates=two_qubit_gates,
            logical_depth=logical_depth,
            observables=len(self.readout.observables),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "q": self.q,
            "R": self.R,
            "L": self.L,
            "encoding": {
                "name": self.encoding.name,
                "rotations": list(self.encoding.rotations),
                "trainable_scale": self.encoding.trainable_scale,
            },
            "readout": {
                "observables": list(self.readout.observables),
                "trainable_weights": self.readout.trainable_weights,
                "trainable_bias": self.readout.trainable_bias,
            },
            "family": self.family.value,
            "trainable_rotations": list(self.trainable_rotations),
        }

    def to_json(self) -> str:
        """Return stable JSON for manifests and experiment records."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


# Short aliases make the contract easy to discover without duplicating types.
CircuitSpec = QuantumAdapterConfig
CircuitConfiguration = QuantumAdapterConfig


class QuantumExecutionAdapter(Protocol):
    """Backend-neutral execution protocol implemented by a runner."""

    config: QuantumAdapterConfig

    def execute(
        self,
        features: np.ndarray,
        parameters: np.ndarray,
        *,
        shots: int | None = None,
    ) -> np.ndarray:
        """Execute and return readout values in observable order."""


class BackendNeutralAdapter:
    """Validation-only placeholder until a concrete backend is selected.

    Keeping this class executable-but-unimplemented prevents accidental
    coupling to Qiskit, PennyLane, or a simulator during contract tests.
    """

    def __init__(self, config: QuantumAdapterConfig) -> None:
        if not isinstance(config, QuantumAdapterConfig):
            raise TypeError("config must be a QuantumAdapterConfig")
        self.config = config

    def execute(
        self,
        features: np.ndarray,
        parameters: np.ndarray,
        *,
        shots: int | None = None,
    ) -> np.ndarray:
        """Reject execution until a backend-specific adapter is provided."""

        if not isinstance(features, np.ndarray) or not isinstance(parameters, np.ndarray):
            raise TypeError("features and parameters must be NumPy arrays")
        if shots is not None and (not isinstance(shots, int) or isinstance(shots, bool) or shots < 1):
            raise ValueError("shots must be a positive integer when provided")
        expected = self.config.resources().trainable_parameters
        if parameters.size != expected:
            raise ValueError(f"expected {expected} trainable parameters, received {parameters.size}")
        raise NotImplementedError(
            "execution is backend-neutral; provide a concrete adapter for a simulator or QPU"
        )


__all__ = [
    "BackendNeutralAdapter",
    "CircuitConfiguration",
    "CircuitSpec",
    "EncodingSpec",
    "EntanglementFamily",
    "LogicalResources",
    "QuantumAdapterConfig",
    "QuantumExecutionAdapter",
    "ReadoutSpec",
    "entangling_pairs",
]
