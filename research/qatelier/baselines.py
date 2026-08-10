"""Dependency-light specifications for QAtelier classical controls.

This module deliberately describes baselines rather than implementing their
training loops.  That keeps the experimental protocol importable in a clean
Python environment and leaves the choice of numerical backend to the runner.
The two budget objects make the fairness contract explicit: every control is
to be resolved against the selected quantum adapter's trainable parameter and
search budgets.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
import json
from typing import Any


def _json_ready(value: Any) -> Any:
    """Convert the small set of values used by specs into JSON data."""

    if hasattr(value, "to_dict"):
        return _json_ready(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_ready(item) for item in value]
    return value


@dataclass(frozen=True)
class ParameterBudget:
    """How a baseline's trainable parameter count is matched.

    ``target_count`` is intentionally optional: the concrete count is a
    property of the selected quantum adapter and input/output dimensions, so
    it is resolved by an experiment runner rather than hard-coded here.
    """

    mode: str = "exact"
    reference: str = "selected_quantum_adapter"
    target_count: int | None = None
    tolerance: int = 0
    include_bias: bool = True
    count_formula: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"exact", "within_tolerance", "unmatched"}:
            raise ValueError(f"unsupported parameter matching mode: {self.mode!r}")
        if self.target_count is not None and self.target_count < 0:
            raise ValueError("target_count must be non-negative")
        if self.tolerance < 0:
            raise ValueError("tolerance must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "reference": self.reference,
            "target_count": self.target_count,
            "tolerance": self.tolerance,
            "include_bias": self.include_bias,
            "count_formula": self.count_formula,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass(frozen=True)
class SearchBudget:
    """How hyperparameter search and model selection are matched."""

    mode: str = "matched"
    reference: str = "selected_quantum_adapter"
    max_trials: int | None = None
    max_training_steps: int | None = None
    max_wall_clock_seconds: float | None = None
    selection_split: str = "validation"
    selection_metric: str = "pre_registered_primary_metric"

    def __post_init__(self) -> None:
        if self.mode not in {"matched", "fixed", "unmatched"}:
            raise ValueError(f"unsupported search matching mode: {self.mode!r}")
        for name in ("max_trials", "max_training_steps"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.max_wall_clock_seconds is not None and self.max_wall_clock_seconds < 0:
            raise ValueError("max_wall_clock_seconds must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "reference": self.reference,
            "max_trials": self.max_trials,
            "max_training_steps": self.max_training_steps,
            "max_wall_clock_seconds": self.max_wall_clock_seconds,
            "selection_split": self.selection_split,
            "selection_metric": self.selection_metric,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass(frozen=True)
class BaselineSpec:
    """A backend-neutral description of one classical comparison model."""

    name: str
    family: str
    description: str
    hyperparameters: Mapping[str, Any] = field(default_factory=dict)
    parameter_budget: ParameterBudget = field(default_factory=ParameterBudget)
    search_budget: SearchBudget = field(default_factory=SearchBudget)
    aliases: tuple[str, ...] = ()
    optional_dependencies: tuple[str, ...] = ()
    trainable: bool = True

    def __post_init__(self) -> None:
        if not self.name or self.name != _normalise_name(self.name):
            raise ValueError("baseline names must be non-empty snake_case identifiers")
        if not self.family:
            raise ValueError("baseline family must be non-empty")
        object.__setattr__(self, "hyperparameters", dict(self.hyperparameters))
        object.__setattr__(self, "aliases", tuple(_normalise_name(alias) for alias in self.aliases))
        object.__setattr__(self, "optional_dependencies", tuple(self.optional_dependencies))

    @property
    def parameter_matching(self) -> ParameterBudget:
        """Compatibility spelling for callers focused on matching metadata."""

        return self.parameter_budget

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "family": self.family,
            "description": self.description,
            "hyperparameters": _json_ready(self.hyperparameters),
            "parameter_budget": self.parameter_budget.to_dict(),
            "search_budget": self.search_budget.to_dict(),
            "aliases": list(self.aliases),
            "optional_dependencies": list(self.optional_dependencies),
            "trainable": self.trainable,
        }


def _normalise_name(name: str) -> str:
    """Normalise human-friendly aliases without changing canonical names."""

    if not isinstance(name, str):
        raise TypeError("baseline name must be a string")
    return name.strip().lower().replace("-", "_").replace(" ", "_")


class BaselineRegistry(Mapping[str, BaselineSpec]):
    """An ordered, alias-aware registry of :class:`BaselineSpec` objects."""

    schema_version = 1

    def __init__(self, specs: Iterator[BaselineSpec] | tuple[BaselineSpec, ...] = ()) -> None:
        self._specs: dict[str, BaselineSpec] = {}
        self._aliases: dict[str, str] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: BaselineSpec) -> BaselineSpec:
        if not isinstance(spec, BaselineSpec):
            raise TypeError("registry entries must be BaselineSpec instances")
        if spec.name in self._specs:
            raise ValueError(f"baseline already registered: {spec.name!r}")
        if spec.name in self._aliases or any(alias in self._specs for alias in spec.aliases):
            raise ValueError(f"baseline name conflicts with an alias: {spec.name!r}")
        for alias in spec.aliases:
            if alias in self._aliases or alias in self._specs:
                raise ValueError(f"baseline alias already registered: {alias!r}")
        self._specs[spec.name] = spec
        self._aliases.update({alias: spec.name for alias in spec.aliases})
        return spec

    def __getitem__(self, name: str) -> BaselineSpec:
        key = _normalise_name(name)
        canonical = self._aliases.get(key, key)
        try:
            return self._specs[canonical]
        except KeyError as exc:
            raise KeyError(f"unknown baseline: {name!r}") from exc

    def __iter__(self) -> Iterator[str]:
        return iter(self._specs)

    def __len__(self) -> int:
        return len(self._specs)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._specs)

    def list(self) -> tuple[BaselineSpec, ...]:
        """Return canonical specs in deterministic registration order."""

        return tuple(self._specs.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "baselines": [spec.to_dict() for spec in self.list()],
        }

    def to_json(self) -> str:
        """Return stable JSON suitable for manifests and experiment logs."""

        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    # Explicit aliases make the serialization contract discoverable to callers.
    as_dict = to_dict
    serialize = to_json


_MATCHED_PARAMETER_BUDGET = ParameterBudget(
    mode="exact",
    reference="selected_quantum_adapter",
    count_formula="resolved_to_equal_trainable_parameter_count",
)
_MATCHED_SEARCH_BUDGET = SearchBudget(
    mode="matched",
    reference="selected_quantum_adapter",
)


def _default_specs() -> tuple[BaselineSpec, ...]:
    """Build the canonical classical-control catalogue."""

    common = {
        "parameter_budget": _MATCHED_PARAMETER_BUDGET,
        "search_budget": _MATCHED_SEARCH_BUDGET,
        "optional_dependencies": ("a numerical backend supplied by the runner",),
    }
    return (
        BaselineSpec(
            name="linear",
            family="linear",
            description="Regularized linear readout over the shared compressed representation.",
            hyperparameters={"regularization": "tuned_on_validation", "fit_intercept": True},
            aliases=("linear_readout",),
            **common,
        ),
        BaselineSpec(
            name="rbf",
            family="rbf",
            description="RBF kernel or finite-center control with capacity resolved to the matched budget.",
            hyperparameters={"kernel": "rbf", "gamma": "tuned_on_validation", "centers": "budget_matched"},
            aliases=("radial_basis",),
            **common,
        ),
        BaselineSpec(
            name="polynomial",
            family="polynomial",
            description="Polynomial feature control for explicit low-order interactions.",
            hyperparameters={"kernel": "polynomial", "degree": "tuned_on_validation", "regularization": "tuned_on_validation"},
            aliases=("poly",),
            **common,
        ),
        BaselineSpec(
            name="random_fourier",
            family="random_fourier",
            description="Random-Fourier feature control with feature count and seed pre-registered.",
            hyperparameters={"features": "budget_matched", "kernel": "rbf", "seed": "pre_registered"},
            aliases=("random_fourier_features", "rff"),
            **common,
        ),
        BaselineSpec(
            name="mlp",
            family="mlp",
            description="Small multilayer perceptron with width and depth resolved to the matched budget.",
            hyperparameters={"hidden_layers": "budget_matched", "activation": "relu", "regularization": "tuned_on_validation"},
            aliases=("feedforward",),
            **common,
        ),
        BaselineSpec(
            name="bilinear",
            family="bilinear",
            description="Bilinear second-order interaction control with rank matched to the adapter budget.",
            hyperparameters={"interaction_order": 2, "rank": "budget_matched", "regularization": "tuned_on_validation"},
            aliases=("second_order",),
            **common,
        ),
        BaselineSpec(
            name="spectrum_matched",
            family="spectrum_matched",
            description="Classical control matched to the selected adapter's measured feature spectrum.",
            hyperparameters={"spectrum_source": "selected_quantum_adapter", "matching_statistic": "pre_registered", "seed": "pre_registered"},
            aliases=("spectrum_matched_control",),
            **common,
        ),
    )


def build_default_registry() -> BaselineRegistry:
    """Return a fresh registry containing all canonical QAtelier controls."""

    return BaselineRegistry(_default_specs())


def list_baselines(registry: BaselineRegistry | None = None) -> tuple[BaselineSpec, ...]:
    """List canonical baseline specifications."""

    return (registry or DEFAULT_BASELINE_REGISTRY).list()


def get_baseline(name: str, registry: BaselineRegistry | None = None) -> BaselineSpec:
    """Look up a baseline by canonical name or supported alias."""

    return (registry or DEFAULT_BASELINE_REGISTRY)[name]


DEFAULT_BASELINE_REGISTRY = build_default_registry()
# A concise public alias for callers that prefer a constant-style registry.
BASELINE_REGISTRY = DEFAULT_BASELINE_REGISTRY
DEFAULT_BASELINES = DEFAULT_BASELINE_REGISTRY


__all__ = [
    "BASELINE_REGISTRY",
    "DEFAULT_BASELINE_REGISTRY",
    "DEFAULT_BASELINES",
    "BaselineRegistry",
    "BaselineSpec",
    "ParameterBudget",
    "SearchBudget",
    "build_default_registry",
    "get_baseline",
    "list_baselines",
]
