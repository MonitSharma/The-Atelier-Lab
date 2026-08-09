"""Deterministic, offline acceptance smoke for the shipped Atelier surfaces."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable

from atelier.finder import prepare_finder_action
from atelier.handoff import create_handoff
from atelier.package import package_check
from atelier.runtime import runtime_layout
from atelier.security import validate_shell_command
from atelier.service import AtelierService
from atelier.web import render_index
from atelier.workflows import list_workflows
from agent.project_memory import ProjectMemoryStore
from tools.registry import create_default_registry
from tools.research import lookup_research
from tools.science import inspect_qasm_text, validate_optimization


@dataclass(frozen=True)
class AcceptanceCheck:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _check(name: str, function: Callable[[], str]) -> AcceptanceCheck:
    try:
        return AcceptanceCheck(name, True, function())
    except Exception as exc:  # noqa: BLE001 - acceptance reports all failures
        return AcceptanceCheck(name, False, str(exc))


def run_acceptance(root: str | Path) -> dict[str, Any]:
    base = Path(root).expanduser().resolve()
    checks = [
        _check("package", lambda: str(package_check(base))),
        _check("service", lambda: str(AtelierService().health())),
        _check("workflows", lambda: f"{len(list_workflows())} workflows"),
        _check("qasm", lambda: str(inspect_qasm_text("OPENQASM 2.0; qreg q[1]; h q[0];"))),
        _check("optimization", lambda: str(validate_optimization({"objective": {"x": 1}, "solution": {"x": 1}, "constraints": []}))),
        _check("security", lambda: str(validate_shell_command("python -m pytest"))),
        _check("research-local-only", lambda: str(lookup_research({"query": "acceptance"}))),
        _check("web", lambda: "Workbench" if "Atelier Workbench" in render_index() else "missing UI"),
        _check("registry", lambda: str(create_default_registry().execute("calculator", {"expression": "2+2"}))),
        _check("finder", lambda: str(prepare_finder_action("explain_file", base / "README.md"))),
        _check("handoff", lambda: str(create_handoff("codex", "acceptance", constraints=["local review"]))),
    ]
    with tempfile.TemporaryDirectory(prefix="atelier_acceptance_") as temp:
        memory = ProjectMemoryStore(Path(temp) / "memory.sqlite3")
        item = memory.remember("acceptance", "preserve evidence", kind="decision")
        checks.append(_check("project-memory", lambda: f"{len(memory.list('acceptance'))} item {item.id}"))
        layout = runtime_layout(Path(temp) / "home").initialize()
        checks.append(_check("runtime-recovery", lambda: str(layout.validate())))
    return {"status": "passed" if all(check.passed for check in checks) else "failed",
            "checks": [check.to_dict() for check in checks]}
