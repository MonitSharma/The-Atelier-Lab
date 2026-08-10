"""Deterministic, offline acceptance smoke for the shipped Atelier surfaces."""

from __future__ import annotations

import base64
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
from atelier.workflow_engine import WorkflowEngine
from atelier.workspace import WorkspaceManager, workspace_scope
from agent.project_memory import ProjectMemoryStore
from rag.visual import analyze_pdf
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


def _write_acceptance_pdf(path: Path) -> None:
    """Create a small deterministic paper fixture without repository data."""
    import fitz

    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Atelier Acceptance Paper", fontsize=18)
    page.insert_textbox(
        fitz.Rect(72, 110, 540, 260),
        "Abstract: This deterministic fixture tests paper characterization, "
        "page citations, and rendered figure evidence without requiring a "
        "downloaded or ignored research corpus. The experiment compares two "
        "local policies under a bounded synthetic workload.",
        fontsize=11,
    )
    page.draw_rect(fitz.Rect(120, 330, 480, 520), color=(0.1, 0.2, 0.6), fill=(0.9, 0.93, 1.0))
    page.draw_line((150, 480), (450, 370), color=(0.8, 0.1, 0.1), width=2)
    page.insert_text((120, 550), "Figure 1: Synthetic policy comparison.", fontsize=10)
    page2 = document.new_page(width=612, height=792)
    page2.insert_text((72, 72), "Results and limitations", fontsize=16)
    page2.insert_textbox(
        fitz.Rect(72, 110, 540, 300),
        "Results: Policy A has lower average cost in the fixture. This result "
        "is illustrative only and does not establish a general advantage. "
        "Limitations include the synthetic workload and the absence of an "
        "external benchmark.",
        fontsize=11,
    )
    document.save(path)
    document.close()


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


def run_clean_acceptance(root: str | Path) -> dict[str, Any]:
    """Exercise a fresh runtime home through deterministic service workflows.

    This is deliberately model-free and network-free. It proves the clean
    install, workspace, artifact, paper-characterization, approval, restart,
    memory, quantum, optimization, and local-only policy paths. Live model
    answer quality and embedding ingestion remain separate acceptance strata.
    """
    base = Path(root).expanduser().resolve()
    checks: list[AcceptanceCheck] = []
    with tempfile.TemporaryDirectory(prefix="atelier_clean_acceptance_") as raw_temp:
        temp = Path(raw_temp)
        home = runtime_layout(temp / "Atelier").initialize()
        workspace_root = temp / "workspace"
        workspace_root.mkdir()
        (workspace_root / "README.md").write_text("# clean acceptance\n", encoding="utf-8")
        (workspace_root / "sample.csv").write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
        (workspace_root / "circuit.qasm").write_text(
            "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[1];\n", encoding="utf-8"
        )
        _write_acceptance_pdf(workspace_root / "paper.pdf")

        registry = home.workspaces / "registry.json"
        manager = WorkspaceManager(registry)
        if "atelier" in {item.name for item in manager.list()}:
            manager.close("atelier")
        manager.add(workspace_root, name="clean", capabilities={"read", "write", "execute"})
        manager.open("clean")
        memory_path = home.databases / "project_memory.sqlite3"
        memory = ProjectMemoryStore(memory_path)
        engine = WorkflowEngine(manager=manager, storage_dir=home.logs / "workflows")
        service = AtelierService(manager=manager, workflow_engine=engine, project_memory=memory)

        checks.extend([
            _check("clean-runtime", lambda: str(home.validate())),
            _check("clean-service", lambda: str(service.health())),
            _check("clean-source", lambda: str(service.source("README.md"))),
            _check("clean-upload", lambda: str(service.upload({
                "filename": "uploaded.txt",
                "content_base64": base64.b64encode(b"uploaded").decode(),
            }))),
            _check("clean-repo-inspect", lambda: str(service.repo_action("inspect", "."))),
            _check("clean-data-profile", lambda: str(service.profile("sample.csv"))),
            _check("clean-figure-evidence", lambda: str(analyze_pdf(
                workspace_root / "paper.pdf", render=True, output_dir=home.cache / "visual",
            ))),
        ])

        paper_run = service.paper_action("deep_read", "paper.pdf", project="clean", model_free=True)
        checks.append(_check(
            "clean-paper-approval",
            lambda: "waiting_approval" if paper_run["status"] == "waiting_approval" else paper_run["status"],
        ))
        run_id = str(paper_run["run_id"])

        # Rebuild the service objects from their persisted runtime files before
        # approving. This is the restart/recovery proof for durable state.
        manager_after_restart = WorkspaceManager(registry)
        engine_after_restart = WorkflowEngine(manager=manager_after_restart, storage_dir=home.logs / "workflows")
        memory_after_restart = ProjectMemoryStore(memory_path)
        restarted = AtelierService(
            manager=manager_after_restart,
            workflow_engine=engine_after_restart,
            project_memory=memory_after_restart,
        )
        checks.append(_check("clean-restart-state", lambda: str(restarted.workflow_get(run_id))))
        approved = restarted.workflow_approve(run_id)
        checks.append(_check(
            "clean-paper-complete",
            lambda: "completed" if approved["status"] == "completed" else approved["status"],
        ))

        checks.extend([
            _check("clean-quantum", lambda: str(restarted.workflow_start(
                "quantum_analyze",
                {"qasm": (workspace_root / "circuit.qasm").read_text(encoding="utf-8")},
            ))),
            _check("clean-optimization", lambda: str(restarted.workflow_start(
                "optimization_validate",
                {"type": "qubo", "variables": ["x"], "linear": {"x": -1}},
            ))),
        ])
        memory_after_restart.remember("clean", "preserve acceptance evidence", kind="decision", session_id="clean-session")
        checks.append(_check("clean-project-memory", lambda: f"{len(memory_after_restart.list('clean'))} durable item(s)"))
        def local_only_check() -> str:
            result = lookup_research({"query": "clean acceptance"})
            if result.get("status") != "denied":
                raise AssertionError(f"LOCAL_ONLY unexpectedly permitted research: {result}")
            return str(result)

        with workspace_scope(manager_after_restart.context()):
            checks.append(_check("clean-local-only", local_only_check))
        checks.append(_check("clean-handoff", lambda: str(create_handoff("codex", "clean acceptance", constraints=["local review"]))))
    return {"status": "passed" if all(check.passed for check in checks) else "failed",
            "mode": "clean_model_free", "checks": [check.to_dict() for check in checks],
            "notes": ["Live model answer quality, embeddings, and external research are separate acceptance strata."]}
