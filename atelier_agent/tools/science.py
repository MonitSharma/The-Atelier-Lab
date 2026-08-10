"""Deterministic quantum-circuit and optimization checks."""

from __future__ import annotations

import ast
import itertools
import math
import re
from typing import Any

import numpy as np

from tools.base import Tool
from tools.files import _resolve_workspace_path


def _qasm_fallback(text: str) -> dict[str, Any]:
    qreg = re.search(r"qreg\s+\w+\[(\d+)\]", text)
    creg = re.search(r"creg\s+\w+\[(\d+)\]", text)
    gates: dict[str, int] = {}
    measurements = 0
    two_qubit_gates = 0
    statements = text.replace(";", ";\n").splitlines()
    for line in statements:
        line = line.split("//", 1)[0].strip()
        match = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)\s+", line)
        if not match or match.group(1) in {"OPENQASM", "include", "qreg", "creg", "barrier"}:
            continue
        name = match.group(1)
        gates[name] = gates.get(name, 0) + 1
        measurements += name == "measure"
        two_qubit_gates += len(re.findall(r"\w+\[\d+\]", line)) == 2
    return {
        "status": "success", "parser": "openqasm2-minimal", "qubits": int(qreg.group(1)) if qreg else None,
        "classical_bits": int(creg.group(1)) if creg else None, "depth": sum(gates.values()),
        "two_qubit_gates": two_qubit_gates,
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
            "two_qubit_gates": sum(int(item.operation.num_qubits == 2) for item in circuit.data),
            "gate_counts": {str(k): int(v) for k, v in circuit.count_ops().items()},
            "measurements": sum(1 for item in circuit.data if item.operation.name == "measure"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error_type": "invalid_qasm", "message": str(exc)}


def _qasm_operations(text: str) -> tuple[int, list[tuple[str, list[float], list[int]]]]:
    qreg = re.search(r"qreg\s+\w+\[(\d+)\]", text)
    if not qreg:
        raise ValueError("QASM must declare a qreg.")
    operations: list[tuple[str, list[float], list[int]]] = []
    for raw in text.replace(";", ";\n").splitlines():
        line = raw.split("//", 1)[0].strip().rstrip(";")
        match = re.match(r"([a-zA-Z][a-zA-Z0-9_]*)(?:\(([^)]*)\))?\s+(.+)$", line)
        if not match or match.group(1) in {"OPENQASM", "include", "qreg", "creg", "barrier"}:
            continue
        name, raw_params, raw_qubits = match.groups()
        params = []
        for value in (raw_params or "").split(","):
            if value.strip():
                expression = value.strip().replace("pi", str(math.pi))
                if not re.fullmatch(r"[0-9eE+*/.() -]+", expression):
                    raise ValueError(f"Unsupported angle expression: {value}")
                params.append(_safe_arithmetic(expression))
        qubits = [int(index) for index in re.findall(r"\w+\[(\d+)\]", raw_qubits)]
        operations.append((name.lower(), params, qubits))
    return int(qreg.group(1)), operations


def _safe_arithmetic(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError("unsupported arithmetic expression")

    return visit(tree)


def simulate_qasm_text(text: str, *, shots: int = 1024) -> dict[str, Any]:
    """Simulate common small OpenQASM circuits with a local NumPy statevector."""
    if not isinstance(shots, int) or not 1 <= shots <= 1_000_000:
        shots = 1024
    try:
        qubits, operations = _qasm_operations(text)
        if qubits > 12:
            return {"status": "error", "error_type": "simulation_limit", "message": "Fallback simulation is limited to 12 qubits."}
        state = np.zeros(2**qubits, dtype=complex)
        state[0] = 1.0

        def single(matrix: np.ndarray, target: int) -> None:
            for index in range(len(state)):
                if not (index & (1 << target)):
                    partner = index | (1 << target)
                    a, b = state[index], state[partner]
                    state[index], state[partner] = matrix[0, 0] * a + matrix[0, 1] * b, matrix[1, 0] * a + matrix[1, 1] * b

        for name, params, operands in operations:
            if name in {"measure", "barrier"}:
                continue
            if len(operands) == 1:
                target = operands[0]
                theta = params[0] if params else 0.0
                matrices = {
                    "id": np.eye(2), "x": np.array([[0, 1], [1, 0]]),
                    "y": np.array([[0, -1j], [1j, 0]]), "z": np.diag([1, -1]),
                    "h": np.array([[1, 1], [1, -1]]) / np.sqrt(2),
                    "s": np.diag([1, 1j]), "t": np.diag([1, np.exp(1j * math.pi / 4)]),
                    "rx": np.array([[np.cos(theta / 2), -1j * np.sin(theta / 2)], [-1j * np.sin(theta / 2), np.cos(theta / 2)]]),
                    "ry": np.array([[np.cos(theta / 2), -np.sin(theta / 2)], [np.sin(theta / 2), np.cos(theta / 2)]]),
                    "rz": np.diag([np.exp(-1j * theta / 2), np.exp(1j * theta / 2)]),
                }
                if name not in matrices:
                    return {"status": "error", "error_type": "unsupported_gate", "message": name}
                single(matrices[name], target)
            elif len(operands) == 2 and name in {"cx", "cnot", "cz", "swap"}:
                control, target = operands
                for index in range(len(state)):
                    if name in {"cx", "cnot"} and (index & (1 << control)) and not (index & (1 << target)):
                        partner = index | (1 << target)
                        state[index], state[partner] = state[partner], state[index]
                    elif name == "cz" and (index & (1 << control)) and (index & (1 << target)):
                        state[index] *= -1
                    elif name == "swap" and (index & (1 << control)) != (index & (1 << target)):
                        partner = index ^ (1 << control) ^ (1 << target)
                        if index < partner:
                            state[index], state[partner] = state[partner], state[index]
            else:
                return {"status": "error", "error_type": "unsupported_gate", "message": name}
        probabilities = np.abs(state) ** 2
        nonzero = {format(index, f"0{qubits}b"): round(float(probability), 8) for index, probability in enumerate(probabilities) if probability > 1e-8}
        return {"status": "success", "simulator": "numpy-statevector", "qubits": qubits,
                "shots": shots, "probabilities": nonzero, "normalization": round(float(probabilities.sum()), 8)}
    except (TypeError, ValueError, SyntaxError, ZeroDivisionError) as exc:
        return {"status": "error", "error_type": "invalid_qasm", "message": str(exc)}


def transpile_qasm_text(text: str, *, optimization_level: int = 1) -> dict[str, Any]:
    """Transpile with Qiskit when installed, otherwise report a safe fallback."""
    inspected = inspect_qasm_text(text)
    if inspected.get("status") != "success":
        return inspected
    try:
        from qiskit import QuantumCircuit, transpile
    except ImportError:
        return {
            "status": "unavailable", "error_type": "dependency_unavailable",
            "capability": "qiskit_transpile", "fallback": inspected,
            "message": "Install the optional quantum dependency to transpile circuits.",
        }
    try:
        circuit = QuantumCircuit.from_qasm_str(text)
        level = max(0, min(int(optimization_level), 3))
        result = transpile(circuit, optimization_level=level)
        return {
            "status": "success", "tool": "quantum_transpile", "parser": "qiskit",
            "optimization_level": level, "qubits": result.num_qubits,
            "depth": result.depth(), "two_qubit_gates": sum(
                int(item.operation.num_qubits == 2) for item in result.data
            ), "gate_counts": {str(k): int(v) for k, v in result.count_ops().items()},
        }
    except Exception as exc:  # noqa: BLE001 - return structured optional capability result
        return {"status": "error", "error_type": "transpile_failed", "message": str(exc)}


def compare_quantum_backends(text: str, backends: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare circuit resources against explicit backend capacity profiles.

    This is a provider-free planning comparison. It never contacts a backend;
    callers supply the capacity facts they want to compare.
    """
    inspected = inspect_qasm_text(text)
    if inspected.get("status") != "success":
        return inspected
    if not isinstance(backends, list) or not backends:
        return {"status": "error", "error_type": "invalid_arguments", "message": "Provide at least one backend capacity profile."}
    rows = []
    for backend in backends:
        if not isinstance(backend, dict) or not isinstance(backend.get("name"), str):
            return {"status": "error", "error_type": "invalid_arguments", "message": "Each backend needs a name."}
        max_qubits = backend.get("max_qubits")
        max_depth = backend.get("max_depth")
        max_two_qubit = backend.get("max_two_qubit_gates")
        limits = {
            "qubits": inspected.get("qubits") is None or max_qubits is None or inspected["qubits"] <= max_qubits,
            "depth": max_depth is None or inspected["depth"] <= max_depth,
            "two_qubit_gates": max_two_qubit is None or inspected["two_qubit_gates"] <= max_two_qubit,
        }
        rows.append({"name": backend["name"], "limits": limits, "fits": all(limits.values()), "profile": backend})
    return {"status": "success", "tool": "quantum_compare_backends", "circuit": inspected, "backends": rows}


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


def run_quantum_transpile(arguments: dict[str, Any]) -> dict[str, Any]:
    text = arguments.get("qasm")
    if text is None and isinstance(arguments.get("path"), str):
        try:
            text = _resolve_workspace_path(arguments["path"], "read").read_text(encoding="utf-8")
        except (ValueError, OSError) as exc:
            return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}
    return transpile_qasm_text(text, optimization_level=int(arguments.get("optimization_level", 1)))


def run_quantum_compare_backends(arguments: dict[str, Any]) -> dict[str, Any]:
    text = arguments.get("qasm")
    if text is None and isinstance(arguments.get("path"), str):
        try:
            text = _resolve_workspace_path(arguments["path"], "read").read_text(encoding="utf-8")
        except (ValueError, OSError) as exc:
            return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}
    return compare_quantum_backends(text, arguments.get("backends", []))


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


def solve_optimization(problem: dict[str, Any]) -> dict[str, Any]:
    """Solve small LPs with SciPy or binary QUBOs by exact enumeration."""
    kind = str(problem.get("type", "lp")).lower()
    sense = str(problem.get("sense", "minimize")).lower()
    if kind == "qubo":
        variables = problem.get("variables") or sorted(set(problem.get("linear", {})) | {item for pair in problem.get("quadratic", {}) for item in pair.split(",")} )
        if not isinstance(variables, list) or len(variables) > 20:
            return {"status": "error", "error_type": "qubo_limit", "message": "Exact local QUBO solving supports at most 20 binary variables."}
        linear = problem.get("linear", {})
        quadratic = problem.get("quadratic", {})
        candidates = []
        for values in itertools.product((0, 1), repeat=len(variables)):
            solution = dict(zip(variables, values, strict=True))
            value = sum(_number(linear.get(var, 0)) * solution[var] for var in variables)
            for pair, coefficient in quadratic.items():
                left, right = [part.strip() for part in pair.split(",", 1)]
                value += _number(coefficient) * solution[left] * solution[right]
            candidates.append((value, solution))
        best = min(candidates, key=lambda item: item[0]) if sense != "maximize" else max(candidates, key=lambda item: item[0])
        return {"status": "success", "solver": "exact-binary-enumeration", "kind": "qubo", "objective_value": best[0], "solution": best[1], "sense": sense, "evaluated": len(candidates)}
    try:
        from scipy.optimize import linprog
    except ImportError:
        return {"status": "error", "error_type": "solver_unavailable", "message": "Install scipy for LP solving."}
    variables = problem.get("variables") or sorted(problem.get("objective", {}))
    objective = [_number(problem.get("objective", {}).get(var, 0)) for var in variables]
    if sense == "maximize":
        objective = [-value for value in objective]
    a_ub, b_ub, a_eq, b_eq = [], [], [], []
    for constraint in problem.get("constraints", []):
        row = [_number(constraint.get("coefficients", {}).get(var, 0)) for var in variables]
        relation = constraint.get("relation", "<=")
        rhs = _number(constraint["rhs"])
        if relation == "<=":
            a_ub.append(row)
            b_ub.append(rhs)
        elif relation == ">=":
            a_ub.append([-value for value in row])
            b_ub.append(-rhs)
        elif relation == "=":
            a_eq.append(row)
            b_eq.append(rhs)
        else:
            return {"status": "error", "error_type": "invalid_problem", "message": f"Unsupported relation {relation!r}."}
    bounds = [tuple(problem.get("bounds", {}).get(var, (0, None))) for var in variables]
    result = linprog(objective, A_ub=a_ub or None, b_ub=b_ub or None, A_eq=a_eq or None, b_eq=b_eq or None, bounds=bounds, method="highs")
    if not result.success:
        return {"status": "success", "solver": "scipy-highs", "kind": "lp", "feasible": False, "message": result.message}
    value = float(result.fun if sense != "maximize" else -result.fun)
    return {"status": "success", "solver": "scipy-highs", "kind": "lp", "feasible": True,
            "objective_value": value, "solution": {var: float(result.x[index]) for index, var in enumerate(variables)}, "message": result.message}


def compare_optimization_solutions(problem: dict[str, Any], solutions: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for index, solution in enumerate(solutions):
        checked = validate_optimization({**problem, "solution": solution})
        rows.append({"index": index, "solution": solution, "feasible": checked.get("feasible", False), "objective_value": checked.get("objective_value")})
    feasible = [row for row in rows if row["feasible"]]
    sense = str(problem.get("sense", "minimize")).lower()
    feasible.sort(key=lambda row: row["objective_value"], reverse=sense == "maximize")
    return {"status": "success", "ranking": feasible + [row for row in rows if not row["feasible"]], "best": feasible[0] if feasible else None}


def run_optimization_validate(arguments: dict[str, Any]) -> dict[str, Any]:
    problem = arguments.get("problem", arguments)
    return validate_optimization(problem)


def run_optimization_solve(arguments: dict[str, Any]) -> dict[str, Any]:
    problem = arguments.get("problem", arguments)
    return solve_optimization(problem)


def run_optimization_compare(arguments: dict[str, Any]) -> dict[str, Any]:
    problem = arguments.get("problem", {})
    solutions = arguments.get("solutions", [])
    return compare_optimization_solutions(problem, solutions)


QUANTUM_INSPECT_TOOL = Tool(
    name="quantum_inspect", description="Inspect OpenQASM deterministically; use Qiskit when installed and report fallback limits otherwise.",
    input_schema={"type": "object", "properties": {"qasm": {"type": "string"}, "path": {"type": "string"}}, "additionalProperties": False},
    function=run_quantum_inspect,
)
QUANTUM_TRANSPILE_TOOL = Tool(
    name="quantum_transpile", description="Transpile an OpenQASM circuit with optional Qiskit; report dependency limits explicitly.",
    input_schema={"type": "object", "properties": {"qasm": {"type": "string"}, "path": {"type": "string"}, "optimization_level": {"type": "integer"}}, "additionalProperties": False},
    function=run_quantum_transpile,
)
QUANTUM_COMPARE_BACKENDS_TOOL = Tool(
    name="quantum_compare_backends", description="Compare circuit resources against explicit provider-free backend capacity profiles.",
    input_schema={"type": "object", "required": ["backends"], "properties": {"qasm": {"type": "string"}, "path": {"type": "string"}, "backends": {"type": "array"}}, "additionalProperties": False},
    function=run_quantum_compare_backends,
)
OPTIMIZATION_VALIDATE_TOOL = Tool(
    name="optimization_validate", description="Verify a candidate LP/QUBO-style solution's constraints, bounds, and objective value deterministically.",
    input_schema={"type": "object", "properties": {"problem": {"type": "object"}}, "required": ["problem"], "additionalProperties": False},
    function=run_optimization_validate,
)
OPTIMIZATION_SOLVE_TOOL = Tool(
    name="optimization_solve", description="Solve a small LP with SciPy HiGHS or a binary QUBO by exact local enumeration.",
    input_schema={"type": "object", "required": ["problem"], "properties": {"problem": {"type": "object"}}, "additionalProperties": False},
    function=run_optimization_solve,
)
OPTIMIZATION_COMPARE_TOOL = Tool(
    name="optimization_compare", description="Validate and rank explicit candidate optimization solutions.",
    input_schema={"type": "object", "required": ["problem", "solutions"], "properties": {"problem": {"type": "object"}, "solutions": {"type": "array"}}, "additionalProperties": False},
    function=run_optimization_compare,
)
