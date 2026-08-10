from typing import Any

from atelier.security import SecurityBoundary
from atelier.workspace import WorkspaceContext, current_workspace_context, workspace_scope
from tools.ast_edit import AST_EDIT_TOOL
from tools.base import Tool
from tools.calculator import CALCULATOR_TOOL
from tools.code_exec import CODE_EXEC_TOOL
from tools.files import EDIT_FILE_TOOL, READ_FILE_TOOL, WRITE_FILE_TOOL
from tools.knowledge import SEARCH_NOTES_TOOL
from tools.memory_tools import RECALL_TOOL, REMEMBER_TOOL
from tools.repo_map import REPO_MAP_TOOL
from tools.repository import (
    REPO_INSPECT_TOOL,
    REPO_SEARCH_TOOL,
    REPO_STATUS_TOOL,
    REPO_SYMBOLS_TOOL,
    REPO_TESTS_TOOL,
)
from tools.research import (
    DOWNLOAD_PAPER_TOOL,
    RESEARCH_GRAPH_TOOL,
    RESEARCH_LOOKUP_TOOL,
    VERIFY_CITATION_TOOL,
)
from tools.science import (
    OPTIMIZATION_COMPARE_TOOL,
    OPTIMIZATION_SOLVE_TOOL,
    OPTIMIZATION_VALIDATE_TOOL,
    QUANTUM_COMPARE_BACKENDS_TOOL,
    QUANTUM_INSPECT_TOOL,
    QUANTUM_TRANSPILE_TOOL,
)
from tools.search import SEARCH_TOOL
from tools.shell import SHELL_TOOL
from tools.test_runner import TEST_RUNNER_TOOL


class ToolRegistry:
    """
    Store, describe and execute tools available to the agent.
    """

    def __init__(self, workspace: WorkspaceContext | None = None, security: SecurityBoundary | None = None) -> None:
        self._tools: dict[str,Tool] = {}
        self.workspace = workspace
        self.security = security or SecurityBoundary()

    def register(self, tool:Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = tool

    def get(self, name:str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def execute(
            self,
            name:str,
            arguments: dict[str,Any],
            ) -> dict[str, Any]:
        tool = self.get(name)

        if tool is None:
            result = {
                    "status": "error",
                    "error_type": "unknown_tool",
                    "message": f"Unknown tool :{name}",
                    "available_tools" : sorted(self._tools.keys()),
                    }
            self.security.audit(tool=name, status="error", error_type="unknown_tool")
            return self.security.result(name, result)

        try:
            with workspace_scope(self.workspace or current_workspace_context()):
                allowed, reason = self.security.preflight(name, arguments)
                if not allowed:
                    result = {"status": "denied", "error_type": "security_policy", "message": reason}
                    self.security.audit(tool=name, status="denied", error_type="security_policy")
                    return self.security.result(name, result)
                result = tool.function(arguments)
                self.security.audit(tool=name, status=str(result.get("status", "unknown")), error_type=result.get("error_type"))
                return self.security.result(name, result)
        except Exception as exc:
            result = {
                    "status": "error",
                    "error_type": "tool_execution_error",
                    "message" : str(exc),
                    }
            self.security.audit(tool=name, status="error", error_type="tool_execution_error")
            return self.security.result(name, result)


    def prompt_description(self) -> str:
        """
        Return a readable description of all registered tools
        """

        sections: list[str] = []

        for tool in self.list_tools():
            sections.append(
                    "\n".join(
                        [
                            f"Tool name: {tool.name}",
                            f"Description: {tool.description}",
                            f"Input Schema: {tool.input_schema}",
                            ]
                        )
                    )
        return "\n\n".join(sections)


def create_default_registry(
    include_shell: bool = False,
    workspace: WorkspaceContext | None = None,
) -> ToolRegistry:
    """Build the registry the agent uses.

    The full toolbox spans both modes: knowledge (``search_notes``) and build
    (``code_exec``, ``test_runner``, ``repo_map``, file read/write/edit, local
    ``search``). The blunt ``shell`` tool is opt-in via ``include_shell``.
    """
    registry = ToolRegistry(workspace)
    for tool in (
        CALCULATOR_TOOL,
        READ_FILE_TOOL,
        WRITE_FILE_TOOL,
        EDIT_FILE_TOOL,
        AST_EDIT_TOOL,
        SEARCH_TOOL,
        SEARCH_NOTES_TOOL,
        REPO_MAP_TOOL,
        REPO_INSPECT_TOOL,
        REPO_STATUS_TOOL,
        REPO_SYMBOLS_TOOL,
        REPO_SEARCH_TOOL,
        REPO_TESTS_TOOL,
        CODE_EXEC_TOOL,
        TEST_RUNNER_TOOL,
        REMEMBER_TOOL,
        RECALL_TOOL,
        RESEARCH_LOOKUP_TOOL,
        RESEARCH_GRAPH_TOOL,
        VERIFY_CITATION_TOOL,
        DOWNLOAD_PAPER_TOOL,
        QUANTUM_INSPECT_TOOL,
        QUANTUM_TRANSPILE_TOOL,
        QUANTUM_COMPARE_BACKENDS_TOOL,
        OPTIMIZATION_VALIDATE_TOOL,
        OPTIMIZATION_SOLVE_TOOL,
        OPTIMIZATION_COMPARE_TOOL,
    ):
        registry.register(tool)
    if include_shell:
        registry.register(SHELL_TOOL)
    return registry
