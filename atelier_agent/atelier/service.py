"""Application service layer shared by CLI, HTTP, and future UI clients."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from typing import Any

from atelier.config import settings
from atelier.workflow_engine import WorkflowEngine
from atelier.workflows import list_workflows
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
        project_memory: Any | None = None,
    ) -> None:
        self.manager = manager or get_workspace_manager()
        self.registry = registry or create_default_registry(workspace=self.manager.context())
        self.workflow_engine = workflow_engine or WorkflowEngine(manager=self.manager)
        self.project_memory = project_memory

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

    def issue_security_confirmation(self, operation: str) -> dict[str, Any]:
        return {"status": "success", "operation": operation, "confirmation_token": self.registry.security.issue_confirmation(operation)}

    def route(self, task: str) -> dict[str, Any]:
        from agent.capability_router import CapabilityRouter

        return CapabilityRouter().decide(task).to_dict()

    def workflows(self) -> list[dict[str, object]]:
        return [workflow.to_dict() for workflow in list_workflows()]

    def workflow_start(self, workflow: str, input_data: dict[str, Any], *, approved: bool = False) -> dict[str, Any]:
        state = self.workflow_engine.start(workflow, input_data, approved=approved)
        self._record_workflow_state(state.to_dict())
        return state.to_dict()

    def workflow_get(self, run_id: str) -> dict[str, Any]:
        state = self.workflow_engine.get(run_id)
        self._record_workflow_state(state.to_dict())
        return state.to_dict()

    def workflow_approve(self, run_id: str, *, approved: bool = True) -> dict[str, Any]:
        state = self.workflow_engine.approve(run_id, approved=approved)
        self._record_workflow_state(state.to_dict())
        return state.to_dict()

    def workflow_recover(self, run_id: str) -> dict[str, Any]:
        state = self.workflow_engine.recover(run_id)
        self._record_workflow_state(state.to_dict())
        return state.to_dict()

    def workflow_cancel(self, run_id: str) -> dict[str, Any]:
        state = self.workflow_engine.cancel(run_id)
        self._record_workflow_state(state.to_dict())
        return state.to_dict()

    def _record_workflow_state(self, payload: dict[str, Any]) -> None:
        """Mirror task state into project memory without storing conversation text."""
        from agent.project_memory import ProjectMemoryStore

        input_data = payload.get("input", {}) if isinstance(payload.get("input"), dict) else {}
        project = str(input_data.get("project", "default"))
        session_id = input_data.get("session_id")
        store = self.project_memory or ProjectMemoryStore()
        store.upsert_entity(
            project, str(payload["run_id"]), "task", payload,
            status=str(payload.get("status", "unknown")),
        )
        if isinstance(session_id, str) and session_id:
            store.set_active_context(project, session_id)

    def memory_context(self, project: str) -> dict[str, Any]:
        from agent.project_memory import ProjectMemoryStore

        store = self.project_memory or ProjectMemoryStore()
        return {"project": project, "active": store.active_context(project),
                "memory": [item.to_dict() for item in store.list(project)],
                "sessions": store.list_entities(project, entity_type="session"),
                "tasks": store.list_entities(project, entity_type="task"),
                "artifacts": store.list_entities(project, entity_type="artifact")}

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

    def source(self, path: str, *, max_chars: int = 200_000) -> dict[str, Any]:
        resolved = self.manager.context().resolve(path, "read").path
        if not resolved.is_file():
            raise ValueError(f"Source path is not a file: {path}")
        content = resolved.read_text(encoding="utf-8", errors="replace")[:max_chars]
        return {"status": "success", "path": str(resolved), "content": content,
                "truncated": resolved.stat().st_size > len(content.encode("utf-8")),
                "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}

    def upload(self, arguments: dict[str, Any]) -> dict[str, Any]:
        name = arguments.get("filename") or arguments.get("path")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("upload requires filename")
        if isinstance(arguments.get("content_base64"), str):
            try:
                content = base64.b64decode(arguments["content_base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("content_base64 is invalid") from exc
        elif isinstance(arguments.get("content"), str):
            content = arguments["content"].encode("utf-8")
        else:
            raise ValueError("upload requires content or content_base64")
        if len(content) > 50_000_000:
            raise ValueError("upload exceeds the 50 MB limit")
        target = self.manager.context().resolve(name, "write").path
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return {"status": "success", "path": str(target), "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest()}

    def chat(self, task: str, *, start: bool = False, input_data: dict[str, Any] | None = None) -> dict[str, Any]:
        decision = self.route(task)
        result: dict[str, Any] = {"status": "routed", "task": task, "route": decision}
        if start and decision.get("workflow"):
            workflow_input = dict(input_data or {})
            workflow_input.setdefault("task", task)
            result["workflow"] = self.workflow_start(str(decision["workflow"]), workflow_input)
        return result

    def paper_action(
        self, action: str, path: str, *, project: str = "default", model_free: bool = False,
    ) -> dict[str, Any]:
        workflows = {"deep_read": "paper_deep_read", "characterize": "paper_fast", "explain": "paper_fast"}
        workflow = workflows.get(action)
        if workflow is None:
            raise ValueError(f"Unsupported paper action: {action}")
        input_data = {"path": path, "project": project}
        if model_free:
            input_data["model_free"] = True
        return self.workflow_start(workflow, input_data)

    def repo_action(self, action: str, path: str = ".", *, project: str = "default", goal: str = "") -> dict[str, Any]:
        if action == "inspect":
            return self.repo_inspect(path)
        if action == "fix":
            return self.workflow_start("code_fix", {"path": path, "goal": goal, "project": project})
        if action == "tests":
            return self.execute_tool("test_runner", {"path": path})
        raise ValueError(f"Unsupported repository action: {action}")

    def deep_research(
        self,
        question: str,
        *,
        depth: str = "standard",
        project: str = "default",
        sources: list[str] | None = None,
        max_rounds: int | None = None,
        max_sources: int | None = None,
        max_web_pages: int | None = None,
        verify_dois: bool = False,
        model_free: bool = False,
    ) -> dict[str, Any]:
        """Start a durable, bounded deep-research run."""
        input_data: dict[str, Any] = {
            "question": question,
            "depth": depth,
            "project": project,
            "verify_dois": verify_dois,
            "model_free": model_free,
        }
        if sources is not None:
            input_data["sources"] = sources
        if max_rounds is not None:
            input_data["max_rounds"] = max_rounds
        if max_sources is not None:
            input_data["max_sources"] = max_sources
        if max_web_pages is not None:
            input_data["max_web_pages"] = max_web_pages
        return self.workflow_start("research_deep", input_data)

    def finder_action(self, action: str, path: str, *, task: str | None = None) -> dict[str, Any]:
        from atelier.finder import execute_finder_action

        return execute_finder_action(action, path, manager=self.manager, task=task)

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
            if operation == "web_search":
                return self.execute_tool("web_search", {
                    "query": str(arguments["query"]),
                    "max_results": int(arguments.get("max_results", 5)),
                })
            if operation in {"web_fetch", "fetch_webpage"}:
                return self.execute_tool("web_fetch", {
                    "url": str(arguments["url"]),
                    "max_chars": int(arguments.get("max_chars", 20_000)),
                    "max_bytes": int(arguments.get("max_bytes", 2_000_000)),
                })
            if operation in {"chat", "task_input"}:
                return self.chat(str(arguments["task"]), start=bool(arguments.get("start", False)), input_data=arguments.get("input"))
            if operation in {"source", "source_view"}:
                return self.source(str(arguments["path"]))
            if operation in {"upload", "file_upload"}:
                return self.upload(arguments)
            if operation == "paper_action":
                return self.paper_action(str(arguments["action"]), str(arguments["path"]), project=str(arguments.get("project", "default")))
            if operation == "repo_action":
                return self.repo_action(str(arguments["action"]), str(arguments.get("path", ".")), project=str(arguments.get("project", "default")), goal=str(arguments.get("goal", "")))
            if operation in {"research_deep", "deep_research"}:
                raw_sources = arguments.get("sources")
                if raw_sources is not None and not isinstance(raw_sources, list):
                    raise TypeError("sources must be an array")
                return self.deep_research(
                    str(arguments["question"]),
                    depth=str(arguments.get("depth", "standard")),
                    project=str(arguments.get("project", "default")),
                    sources=raw_sources,
                    max_rounds=arguments.get("max_rounds"),
                    max_sources=arguments.get("max_sources"),
                    max_web_pages=arguments.get("max_web_pages"),
                    verify_dois=bool(arguments.get("verify_dois", False)),
                    model_free=bool(arguments.get("model_free", False)),
                )
            if operation == "finder_action":
                return self.finder_action(str(arguments["action"]), str(arguments["path"]), task=arguments.get("task"))
            if operation == "memory":
                return {"memory": self.memory()}
            if operation in {"memory_context", "project_memory"}:
                return self.memory_context(str(arguments.get("project", "default")))
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
            if operation in {"security_confirmation", "approval_request"}:
                return self.issue_security_confirmation(str(arguments["operation"]))
            return {"status": "error", "error_type": "unknown_operation", "message": operation}
        except (KeyError, TypeError, ValueError, OSError) as exc:
            return {"status": "error", "error_type": "service_error", "message": str(exc)}
