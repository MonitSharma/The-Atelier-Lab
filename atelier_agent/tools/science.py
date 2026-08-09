"""Deterministic quantum-circuit and optimization checks."""

from __future__ import annotations

import re
from typing import Any

from tools.base import Tool
from tools.files import _resolve_workspace_path


def _qasm_fallback(text: str) -> dict[str, Any]:
    qreg = re.search(r"qreg\s+\w+\[(\d+)\]", text)
    creg = re.search(r"creg\s+\w+\[(\d+)\]", text)
    gates: dict[str, int] = {}
    measurements = 0
    statements = text.replace(";", ";\n").splitlines()
    for line in statements:
        line = line.split("//", 1)[0].strip()
        match = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)\s+", line)
        if not match or match.group(1) in {"OPENQASM", "include", "qreg", "creg", "barrier"}:
            continue
        name = match.group(1)
        gates[name] = gates.get(name, 0) + 1
        measurements += name == "measure"
    return {
        "status": "success", "parser": "openqasm2-minimal", "qubits": int(qreg.group(1)) if qreg else None,
        "classical_bits": int(creg.group(1)) if creg else None, "depth": sum(gates.values()),
        "gate_counts": gates, "measurements": measurements,
        "warning": "Qiskit is not installed; depth is a conservative gate-count estimate.",
    }


def inspect_qasm_text(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"status": "error", "error_type": "invalid_arguments", "message": "QASM text is required."}
    try:
        from qiskit import QuantumCircuit
    except ImportError:
        return _qasm_fallback(text)
    try:
        circuit = QuantumCircuit.from_qasm_str(text)
        return {
            "status": "success", "parser": "qiskit", "qubits": circuit.num_qubits,
            "classical_bits": circuit.num_clbits, "depth": circuit.depth(),
            "gate_counts": {str(k): int(v) for k, v in circuit.count_ops().items()},
            "measurements": sum(1 for item in circuit.data if item.operation.name == "measure"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error_type": "invalid_qasm", "message": str(exc)}


def run_quantum_inspect(arguments: dict[str, Any]) -> dict[str, Any]:
    text = arguments.get("qasm")
    path = arguments.get("path")
    if text is None and isinstance(path, str):
        try:
            text = _resolve_workspace_path(path, "read").read_text(encoding="utf-8")
        except (ValueError, OSError) as exc:
            return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}
    result = inspect_qasm_text(text)
    result["tool"] = "quantum_inspect"
    return result


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("numeric values are required")
    return float(value)


def validate_optimization(problem: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(problem, dict):
        return {"status": "error", "error_type": "invalid_problem", "message": "Problem must be an object."}
    objective = problem.get("objective", {})
    solution = problem.get("solution", {})
    constraints = problem.get("constraints", [])
    if not isinstance(objective, dict) or not isinstance(solution, dict) or not isinstance(constraints, list):
        return {"status": "error", "error_type": "invalid_problem", "message": "objective, solution, and constraints have invalid types."}
    try:
        objective_value = sum(_number(coef) * _number(solution.get(var, 0)) for var, coef in objective.items())
        checks = []
        for index, constraint in enumerate(constraints):
            coefficients = constraint.get("coefficients", {})
            lhs = sum(_number(coef) * _number(solution.get(var, 0)) for var, coef in coefficients.items())
            rhs = _number(constraint["rhs"])
            relation = constraint.get("relation", "<=")
            satisfied = {"<=": lhs <= rhs, ">=": lhs >= rhs, "=": abs(lhs - rhs) <= 1e-9}.get(relation)
            if satisfied is None:
                raise ValueError(f"constraint {index} has unsupported relation {relation!r}")
            checks.append({"index": index, "relation": relation, "lhs": lhs, "rhs": rhs, "satisfied": satisfied})
        bounds = problem.get("bounds", {})
        for var, bound in bounds.items():
            value = _number(solution.get(var, 0))
            lower = bound[0] if bound and bound[0] is not None else None
            upper = bound[1] if bound and len(bound) > 1 and bound[1] is not None else None
            if lower is not None and value < _number(lower):
                checks.append({"variable": var, "bound": "lower", "value": value, "rhs": lower, "satisfied": False})
            if upper is not None and value > _number(upper):
                checks.append({"variable": var, "bound": "upper", "value": value, "rhs": upper, "satisfied": False})
        feasible = all(check["satisfied"] for check in checks)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return {"status": "error", "error_type": "invalid_problem", "message": str(exc)}
    return {"status": "success", "tool": "optimization_validate", "feasible": feasible,
            "objective_value": objective_value, "checks": checks,
            "sense": problem.get("sense", "minimize")}


def run_optimization_validate(arguments: dict[str, Any]) -> dict[str, Any]:
    problem = arguments.get("problem", arguments)
    return validate_optimization(problem)


QUANTUM_INSPECT_TOOL = Tool(
    name="quantum_inspect", description="Inspect OpenQASM deterministically; use Qiskit when installed and report fallback limits otherwise.",
    input_schema={"type": "object", "properties": {"qasm": {"type": "string"}, "path": {"type": "string"}}, "additionalProperties": False},
    function=run_quantum_inspect,
)
OPTIMIZATION_VALIDATE_TOOL = Tool(
    name="optimization_validate", description="Verify a candidate LP/QUBO-style solution's constraints, bounds, and objective value deterministically.",
    input_schema={"type": "object", "properties": {"problem": {"type": "object"}}, "required": ["problem"], "additionalProperties": False},
    function=run_optimization_validate,
)
