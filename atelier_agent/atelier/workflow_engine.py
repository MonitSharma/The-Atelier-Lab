"""Durable, typed workflow execution for the Atelier workbench.

The engine is intentionally small and deterministic.  It owns workflow state,
checkpoints, approval gates, recovery, and evidence persistence; individual
domain tools remain responsible for the actual scientific or repository work.
Model-driven ReAct remains available as a separate primitive and is invoked by
the ``code_fix`` workflow only after its explicit edit approval gate.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from atelier.config import settings
from atelier.workflows import WorkflowSpec, get_workflow
from atelier.workspace import (
    WorkspaceError,
    WorkspaceManager,
    get_workspace_manager,
    workspace_scope,
)

RunStatus = Literal["queued", "running", "waiting_approval", "completed", "failed", "cancelled"]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


@dataclass(frozen=True)
class WorkflowCheckpoint:
    step_index: int
    step_name: str
    state_digest: str
    outputs: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowState:
    run_id: str
    workflow: str
    status: RunStatus
    input: dict[str, Any]
    step_index: int = 0
    outputs: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    checkpoints: list[WorkflowCheckpoint] = field(default_factory=list)
    approval_required: str | None = None
    approved: bool = False
    error: str | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["checkpoints"] = [checkpoint.to_dict() for checkpoint in self.checkpoints]
        return _jsonable(payload)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorkflowState:
        checkpoints = [WorkflowCheckpoint(**item) for item in payload.get("checkpoints", [])]
        return cls(
            run_id=str(payload["run_id"]), workflow=str(payload["workflow"]),
            status=str(payload["status"]), input=dict(payload.get("input", {})),
            step_index=int(payload.get("step_index", 0)), outputs=dict(payload.get("outputs", {})),
            evidence=list(payload.get("evidence", [])), checkpoints=checkpoints,
            approval_required=payload.get("approval_required"), approved=bool(payload.get("approved", False)),
            error=payload.get("error"), created_at=str(payload.get("created_at", _now())),
            updated_at=str(payload.get("updated_at", _now())),
        )


class WorkflowEngine:
    """Persist and execute the explicit workflows in :mod:`atelier.workflows`."""

    def __init__(self, manager: WorkspaceManager | None = None, storage_dir: str | Path | None = None) -> None:
        self.manager = manager or get_workspace_manager()
        self.storage_dir = Path(storage_dir or settings.workflow_dir).expanduser().resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, run_id: str) -> Path:
        if not run_id or Path(run_id).name != run_id or not run_id.endswith(".json"):
            run_id = f"{run_id}.json" if not run_id.endswith(".json") else run_id
        return self.storage_dir / run_id

    def _save(self, state: WorkflowState) -> WorkflowState:
        state.updated_at = _now()
        destination = self._path(state.run_id)
        fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=str(self.storage_dir), text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state.to_dict(), handle, indent=2)
                handle.write("\n")
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return state

    def get(self, run_id: str) -> WorkflowState:
        path = self._path(run_id)
        try:
            return WorkflowState.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise KeyError(f"Unknown workflow run: {run_id}") from exc
        except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
            raise ValueError(f"Invalid workflow state: {path}") from exc

    def list(self, *, limit: int = 50) -> list[WorkflowState]:
        states: list[WorkflowState] = []
        for path in sorted(self.storage_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                states.append(WorkflowState.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError):
                continue
            if len(states) >= limit:
                break
        return states

    @staticmethod
    def _digest(state: WorkflowState) -> str:
        payload = json.dumps({"run_id": state.run_id, "workflow": state.workflow,
                              "step_index": state.step_index, "outputs": state.outputs,
                              "evidence": state.evidence}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _approval_step(spec: WorkflowSpec, state: WorkflowState, step: str) -> bool:
        if state.approved:
            return False
        if spec.name == "code_fix" and step == "edit":
            return True
        if spec.name in {"paper_deep_read", "paper_compare"} and step in {"synthesize", "report gaps"}:
            return True
        if spec.name == "figure_inspect" and step == "interpret visual":
            return True
        if spec.name == "data_analyze" and step in {"summarize", "cite inputs"}:
            return True
        if spec.name == "research_verify" and (state.input.get("download") or state.input.get("publish")):
            return step == "report uncertainty"
        if spec.name == "quantum_analyze" and state.input.get("backend"):
            return step == "transpile/simulate if available"
        if spec.name == "optimization_validate" and state.input.get("external_solver"):
            return step == "compare solutions"
        return False

    def _resolve_path(self, raw: Any, capability: str = "read") -> Path:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("workflow input requires a non-empty path")
        return self.manager.context().resolve(raw, capability).path

    def _execute_step(self, state: WorkflowState, spec: WorkflowSpec, step: str) -> dict[str, Any]:
        """Execute one typed step and return only JSON-serializable evidence."""
        workflow = spec.name
        if workflow == "repo_inspect":
            from repo.inspector import RepositoryInspector

            path = self._resolve_path(state.input.get("path"), "read")
            inspector = RepositoryInspector.for_path(path)
            if step == "inspect":
                return inspector.inspect()
            if step == "map symbols":
                return {"symbols": inspector.symbols()}
            if step == "find tests":
                return {"test_frameworks": inspector.test_frameworks(), "relationships": inspector.test_relationships()}
            if step == "report state":
                return {"git": inspector.git_status(), "diff": inspector.git_diff()}
        elif workflow in {"paper_fast", "paper_deep_read"}:
            from rag.paper import characterize, extract_pdf_pages

            path = self._resolve_path(state.input.get("path"), "read")
            if step in {"identify", "characterize"}:
                if state.input.get("model_free"):
                    pages = extract_pdf_pages(path)
                    text = "\n".join(str(page.get("text", "")) for page in pages)
                    return {
                        "status": "success",
                        "mode": "model_free",
                        "path": str(path),
                        "pages": len(pages),
                        "characters": len(text),
                        "note": "Deterministic extraction only; model characterization is a separate workflow stage.",
                    }
                return characterize(path)
            if step == "extract":
                return {"path": str(path), "bytes": path.stat().st_size, "extraction": "native PDF extraction"}
            if step in {"cite", "verify citations"}:
                return {"path": str(path), "citation_source": str(path), "verified": False,
                        "note": "Citation verification requires explicit bibliographic metadata."}
            if step in {"retrieve", "inspect figures", "synthesize"}:
                return {"status": "ready", "step": step, "path": str(path)}
        elif workflow == "figure_inspect":
            from rag.visual import analyze_pdf

            path = self._resolve_path(state.input.get("path"), "read")
            if step in {"locate pages", "render evidence"}:
                return analyze_pdf(path, render=step == "render evidence")
            if step == "interpret visual":
                return {"status": "ready", "step": step, "note": "Visual interpretation requires an approved multimodal model input."}
            return {"status": "ready", "step": step, "path": str(path)}
        elif workflow == "paper_compare":
            from rag.paper import characterize

            paths = state.input.get("paths", [])
            if not isinstance(paths, list) or not paths:
                raise ValueError("paper_compare requires a non-empty paths list")
            if step == "characterize each":
                return {str(path): characterize(self._resolve_path(path, "read")) for path in paths}
            return {"status": "ready", "step": step, "papers": len(paths)}
        elif workflow == "data_analyze":
            from files.artifacts import profile_path

            path = self._resolve_path(state.input.get("path"), "read")
            if step in {"profile", "validate"}:
                return profile_path(path).to_dict()
            return {"status": "ready", "step": step, "path": str(path)}
        elif workflow == "research_verify":
            from tools.research import lookup_research, verify_citation

            if step == "query approved source":
                arguments = dict(state.input.get("query", state.input))
                with workspace_scope(self.manager.context()):
                    return lookup_research(arguments)
            if step == "compare local evidence":
                arguments = state.input.get("citation")
                if isinstance(arguments, dict):
                    with workspace_scope(self.manager.context()):
                        return verify_citation(arguments)
                return {"status": "skipped", "reason": "No explicit citation supplied."}
            return {"status": "ready", "step": step}
        elif workflow == "research_deep":
            from agent.research_workflow import DeepResearchWorkflow

            with workspace_scope(self.manager.context()):
                return DeepResearchWorkflow().execute_step(step, state.input, state.outputs)
        elif workflow == "quantum_analyze":
            from tools.science import inspect_qasm_text, simulate_qasm_text

            text = state.input.get("qasm")
            if text is None and state.input.get("path"):
                text = self._resolve_path(state.input["path"], "read").read_text(encoding="utf-8")
            if not isinstance(text, str):
                raise ValueError("quantum_analyze requires qasm or path")
            if step == "parse" or step == "count resources":
                return inspect_qasm_text(text)
            if step == "transpile/simulate if available":
                return simulate_qasm_text(text, shots=int(state.input.get("shots", 1024)))
            return {"status": "ready", "step": step}
        elif workflow == "optimization_validate":
            from tools.science import (
                compare_optimization_solutions,
                solve_optimization,
                validate_optimization,
            )

            problem = state.input.get("problem", state.input)
            if step in {"parse problem", "check feasibility", "compute objective"}:
                return validate_optimization(problem)
            if step == "compare solutions":
                solutions = state.input.get("solutions")
                if isinstance(solutions, list):
                    return compare_optimization_solutions(problem, solutions)
                return solve_optimization(problem)
        elif workflow == "code_fix":
            if step == "inspect":
                from repo.inspector import RepositoryInspector

                return RepositoryInspector.for_path(self._resolve_path(state.input.get("path", "."), "read")).inspect()
            if step == "edit":
                from agent.coding_workflow import BuildWorkflow

                root = self._resolve_path(state.input.get("path", "."), "write")
                result = BuildWorkflow(root, workspace=self.manager.context()).run(
                    str(state.input.get("goal", "")), rollback_on_failure=True,
                )
                return result.certificate.to_dict()
            return {"status": "ready", "step": step}
        return {"status": "recorded", "workflow": workflow, "step": step}

    def _continue(self, state: WorkflowState) -> WorkflowState:
        spec = get_workflow(state.workflow)
        state.status = "running"
        state.error = None
        self._save(state)
        try:
            while state.step_index < len(spec.steps):
                step = spec.steps[state.step_index]
                if self._approval_step(spec, state, step):
                    state.status = "waiting_approval"
                    state.approval_required = step
                    self._save(state)
                    return state
                checkpoint = WorkflowCheckpoint(
                    step_index=state.step_index, step_name=step,
                    state_digest=self._digest(state), outputs=_jsonable(dict(state.outputs)), created_at=_now(),
                )
                state.checkpoints.append(checkpoint)
                result = self._execute_step(state, spec, step)
                state.outputs[step] = _jsonable(result)
                state.evidence.append({"step": step, "status": result.get("status", "success") if isinstance(result, dict) else "success", "result": _jsonable(result), "recorded_at": _now()})
                state.step_index += 1
                state.approval_required = None
                self._save(state)
            state.status = "completed"
            self._save(state)
            return state
        except (WorkspaceError, OSError, ValueError, KeyError, RuntimeError, TypeError) as exc:
            state.status = "failed"
            state.error = str(exc)
            self._save(state)
            return state

    def start(self, workflow: str, input_data: dict[str, Any], *, approved: bool = False) -> WorkflowState:
        get_workflow(workflow)
        run_id = uuid.uuid4().hex
        state = WorkflowState(run_id=run_id, workflow=workflow, status="queued", input=_jsonable(dict(input_data)), approved=approved)
        self._save(state)
        return self._continue(state)

    def approve(self, run_id: str, *, approved: bool = True) -> WorkflowState:
        state = self.get(run_id)
        if state.status != "waiting_approval":
            raise ValueError(f"Workflow is not waiting for approval: {state.status}")
        state.approved = approved
        if not approved:
            state.status = "cancelled"
            state.error = "Human approval was declined."
            return self._save(state)
        return self._continue(state)

    def recover(self, run_id: str) -> WorkflowState:
        state = self.get(run_id)
        if state.status not in {"failed", "running", "waiting_approval"}:
            raise ValueError(f"Workflow cannot be recovered from status: {state.status}")
        if state.checkpoints:
            checkpoint = state.checkpoints[-1]
            state.step_index = checkpoint.step_index
            state.outputs = {key: value for key, value in state.outputs.items() if key in {item.step_name for item in state.checkpoints[:-1]}}
            state.evidence = state.evidence[:checkpoint.step_index]
        state.status = "queued"
        state.error = None
        state.approval_required = None
        state.approved = False
        self._save(state)
        return self._continue(state)

    def cancel(self, run_id: str) -> WorkflowState:
        state = self.get(run_id)
        if state.status in {"completed", "cancelled"}:
            return state
        state.status = "cancelled"
        state.error = "Cancelled by user."
        return self._save(state)
