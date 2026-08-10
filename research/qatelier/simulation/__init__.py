"""Dependency-lazy executable simulators for the QAtelier circuit contract."""

from .simulator import (
    CircuitSchedule,
    OptionalSimulatorDependencyError,
    ParameterLayout,
    PQCStatevectorSimulator,
    ScheduleResources,
    SimulationResult,
    aer_available,
    cross_validate_aer,
    initialize_parameters,
    simulate,
    simulate_batch,
    simulate_with_aer,
)

__all__ = [
    "CircuitSchedule",
    "OptionalSimulatorDependencyError",
    "ParameterLayout",
    "PQCStatevectorSimulator",
    "ScheduleResources",
    "SimulationResult",
    "aer_available",
    "cross_validate_aer",
    "initialize_parameters",
    "simulate",
    "simulate_batch",
    "simulate_with_aer",
]
