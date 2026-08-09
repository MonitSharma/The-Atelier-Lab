from tools.science import inspect_qasm_text, validate_optimization


def test_qasm_fallback_is_deterministic_without_qiskit():
    result = inspect_qasm_text("OPENQASM 2.0;\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n")
    assert result["status"] == "success"
    assert result["qubits"] == 2
    assert result["gate_counts"] == {"h": 1, "cx": 1}
    assert result["parser"] in {"qiskit", "openqasm2-minimal"}


def test_optimization_validation_reports_objective_and_constraints():
    result = validate_optimization({
        "sense": "minimize", "objective": {"x": 2, "y": 1},
        "constraints": [{"coefficients": {"x": 1, "y": 1}, "relation": ">=", "rhs": 3}],
        "bounds": {"x": [0, 10], "y": [0, 10]}, "solution": {"x": 1, "y": 2},
    })
    assert result["status"] == "success"
    assert result["feasible"] is True
    assert result["objective_value"] == 4


def test_optimization_validation_marks_infeasible_solution():
    result = validate_optimization({
        "objective": {"x": 1}, "constraints": [{"coefficients": {"x": 1}, "relation": "<=", "rhs": 2}],
        "solution": {"x": 3},
    })
    assert result["feasible"] is False
