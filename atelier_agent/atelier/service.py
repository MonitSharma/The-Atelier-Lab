"""Application service layer shared by CLI, HTTP, and future UI clients."""

from __future__ import annotations

import json
from typing import Any

from atelier.config import settings
from atelier.workflows import list_workflows
from atelier.workflow_engine import WorkflowEngine
from atelier.workspace import WorkspaceManager, get_workspace_manager
from files.artifacts import profile_path
from repo.inspector import RepositoryInspector
from tools.registry import ToolRegistry, create_default_registry


class AtelierService:
    """Small JSON-friendly facade over Atelier capabilities and policy."""

    def __init__(
        self,
        manager: WorkspaceManager | None = None,
        registry: ToolRegistry | None = None,
        workflow_engine: WorkflowEngine | None = None,
    ) -> None:
        self.manager = manager or get_workspace_manager()
        self.registry = registry or create_default_registry(workspace=self.manager.context())
        self.workflow_engine = workflow_engine or WorkflowEngine(manager=self.manager)

    def health(self) -> dict[str, Any]:
        context = self.manager.context()
        return {"status": "ok", "active_workspace": context.active.name,
                "attached_workspaces": [item.name for item in context.attached]}

    def workspaces(self) -> list[dict[str, object]]:
        return [item.to_dict() for item in self.manager.list()]

    def tools(self) -> list[dict[str, Any]]:
        return [{"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
                for tool in self.registry.list_tools()]

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.registry.execute(name, arguments)

    def route(self, task: str) -> dict[str, Any]:
        from agent.capability_router import CapabilityRouter

        return CapabilityRouter().decide(task).to_dict()

    def workflows(self) -> list[dict[str, object]]:
        return [workflow.to_dict() for workflow in list_workflows()]

    def workflow_start(self, workflow: str, input_data: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        return self.workflow_engine.start(workflow, input_data, approved=approved).to_dict()

    def workflow_get(self, run_id: str) -> dict[str, Any]:
        return self.workflow_engine.get(run_id).to_dict()

    def workflow_approve(self, run_id: str, *, approved: bool = True) -> dict[str, Any]:
        return self.workflow_engine.approve(run_id, approved=approved).to_dict()

    def workflow_recover(self, run_id: str) -> dict[str, Any]:
        return self.workflow_engine.recover(run_id).to_dict()

    def workflow_cancel(self, run_id: str) -> dict[str, Any]:
        return self.workflow_engine.cancel(run_id).to_dict()

    def models(self) -> list[dict[str, Any]]:
        from models.lifecycle import ModelLifecycle

        return [record.to_dict() for record in ModelLifecycle().list()]

    def library(self) -> dict[str, Any]:
        from rag.store import VectorStore

        store = VectorStore()
        return {"count": store.count(), "sources": store.sources()}

    def search(self, query: str, k: int = 6) -> dict[str, Any]:
        from rag.retrieve import retrieve

        hits = retrieve(query, k=k)
        return {"query": query, "results": [{
            "text": hit["text"], "score": hit.get("final_score", hit.get("score")),
            "metadata": hit.get("metadata", {}),
        } for hit in hits]}

    def memory(self) -> list[dict[str, Any]]:
        from agent.memory import get_memory

        return [{"id": item.id, "text": item.text, "tags": item.tags, "created_at": item.created_at}
                for item in get_memory().all()]

    def tasks(self) -> list[dict[str, Any]]:
        tasks = [state.to_dict() for state in self.workflow_engine.list()]
        if settings.traces_dir.exists():
            for path in sorted(settings.traces_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:50]:
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    trace = payload.get("trace", [])
                    tasks.append({"id": path.stem, "goal": payload.get("goal", ""), "steps": len(trace), "path": str(path), "kind": "react_trace"})
                except (OSError, json.JSONDecodeError, TypeError):
                    continue
        return tasks

    def approvals(self) -> list[dict[str, Any]]:
        return [state.to_dict() for state in self.workflow_engine.list() if state.status == "waiting_approval"]

    def profile(self, path: str) -> dict[str, Any]:
        resolved = self.manager.context().resolve(path, "read").path
        return profile_path(resolved).to_dict()

    def repo_inspect(self, path: str = ".") -> dict[str, Any]:
        resolved = self.manager.context().resolve(path, "read").path
        return RepositoryInspector.for_path(resolved).inspect()

    def dispatch(self, operation: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        try:
            if operation == "health":
                return self.health()
            if operation == "workspaces":
                return {"workspaces": self.workspaces()}
            if operation == "tools":
                return {"tools": self.tools()}
            if operation == "workflows":
                return {"workflows": self.workflows()}
            if operation in {"workflow_start", "task_create"}:
                workflow = str(arguments.get("workflow", ""))
                input_data = arguments.get("input", arguments.get("input_data", {}))
                if not isinstance(input_data, dict):
                    raise TypeError("workflow input must be an object")
                return self.workflow_start(workflow, input_data, approved=bool(arguments.get("approved", False)))
            if operation in {"workflow_get", "task_status"}:
                return self.workflow_get(str(arguments["run_id"]))
            if operation in {"workflow_approve", "task_approve"}:
                return self.workflow_approve(str(arguments["run_id"]), approved=bool(arguments.get("approved", True)))
            if operation in {"workflow_recover", "task_recover"}:
                return self.workflow_recover(str(arguments["run_id"]))
            if operation in {"workflow_cancel", "task_cancel"}:
                return self.workflow_cancel(str(arguments["run_id"]))
            if operation == "models":
                return {"models": self.models()}
            if operation == "library":
                return self.library()
            if operation == "search":
                return self.search(str(arguments["query"]), int(arguments.get("k", 6)))
            if operation == "memory":
                return {"memory": self.memory()}
            if operation == "tasks":
                return {"tasks": self.tasks()}
            if operation == "approvals":
                return {"approvals": self.approvals()}
            if operation == "route":
                return self.route(str(arguments["task"]))
            if operation == "profile":
                return self.profile(str(arguments["path"]))
            if operation == "artifacts":
                return self.profile(str(arguments["path"]))
            if operation == "repo_inspect":
                return self.repo_inspect(str(arguments.get("path", ".")))
            if operation == "tool":
                return self.execute_tool(str(arguments["name"]), dict(arguments.get("arguments", {})))
            return {"status": "error", "error_type": "unknown_operation", "message": operation}
        except (KeyError, TypeError, ValueError, OSError) as exc:
            return {"status": "error", "error_type": "service_error", "message": str(exc)}
