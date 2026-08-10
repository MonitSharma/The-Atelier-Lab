from tools.science import (
    compare_optimization_solutions,
    inspect_qasm_text,
    simulate_qasm_text,
    solve_optimization,
    compare_quantum_backends,
    transpile_qasm_text,
    validate_optimization,
)


def test_qasm_fallback_is_deterministic_without_qiskit():
    result = inspect_qasm_text("OPENQASM 2.0;\nqreg q[2];\nh q[0];\ncx q[0],q[1];\n")
    assert result["status"] == "success"
    assert result["qubits"] == 2
    assert result["gate_counts"] == {"h": 1, "cx": 1}
    assert result["two_qubit_gates"] == 1
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


def test_small_circuit_simulation_returns_normalized_bell_state():
    result = simulate_qasm_text("OPENQASM 2.0;\nqreg q[2];\nh q[0];\ncx q[0],q[1];")
    assert result["status"] == "success"
    assert result["normalization"] == 1.0
    assert set(result["probabilities"]) == {"00", "11"}


def test_optional_transpile_reports_dependency_or_resource_result():
    result = transpile_qasm_text("OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];")
    assert result["status"] in {"success", "unavailable"}


def test_provider_free_backend_comparison_uses_explicit_capacity_profiles():
    result = compare_quantum_backends(
        "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];",
        [{"name": "small", "max_qubits": 1}, {"name": "adequate", "max_qubits": 2, "max_depth": 5}],
    )
    assert result["status"] == "success"
    assert [row["fits"] for row in result["backends"]] == [False, True]


def test_qubo_exact_solver_and_candidate_comparison():
    problem = {"type": "qubo", "variables": ["x", "y"], "linear": {"x": -2, "y": -1}, "quadratic": {"x,y": -1}}
    result = solve_optimization(problem)
    assert result["status"] == "success"
    assert result["solution"] == {"x": 1, "y": 1}

    comparison = compare_optimization_solutions(
        {"objective": {"x": 1}, "constraints": [{"coefficients": {"x": 1}, "relation": ">=", "rhs": 0}], "sense": "minimize"},
        [{"x": 2}, {"x": 0}],
    )
    assert comparison["best"]["solution"] == {"x": 0}
