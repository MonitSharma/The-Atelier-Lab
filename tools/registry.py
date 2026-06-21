from typing import Any

from tools.base import Tool
from tools.calculator import CALCULATOR_TOOL
from tools.code_exec import CODE_EXEC_TOOL
from tools.files import EDIT_FILE_TOOL, READ_FILE_TOOL, WRITE_FILE_TOOL
from tools.knowledge import SEARCH_NOTES_TOOL
from tools.repo_map import REPO_MAP_TOOL
from tools.search import SEARCH_TOOL
from tools.shell import SHELL_TOOL
from tools.test_runner import TEST_RUNNER_TOOL


class ToolRegistry:
    """
    Store, describe and execute tools available to the agent.
    """

    def __init__(self) -> None:
        self._tools: dict[str,Tool] = {}

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
            return {
                    "status": "error",
                    "error_type": "unknown_tool",
                    "message": f"Unknown tool :{name}",
                    "available_tools" : sorted(self._tools.keys()),
                    }

        try: 
            return tool.function(arguments)
        except Exception as exc:
            return {
                    "status": "error",
                    "error_type": "tool_execution_error",
                    "message" : str(exc),
                    }


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


def create_default_registry(include_shell: bool = False) -> ToolRegistry:
    """Build the registry the agent uses.

    The full toolbox spans both modes: knowledge (``search_notes``) and build
    (``code_exec``, ``test_runner``, ``repo_map``, file read/write/edit, local
    ``search``). The blunt ``shell`` tool is opt-in via ``include_shell``.
    """
    registry = ToolRegistry()
    for tool in (
        CALCULATOR_TOOL,
        READ_FILE_TOOL,
        WRITE_FILE_TOOL,
        EDIT_FILE_TOOL,
        SEARCH_TOOL,
        SEARCH_NOTES_TOOL,
        REPO_MAP_TOOL,
        CODE_EXEC_TOOL,
        TEST_RUNNER_TOOL,
    ):
        registry.register(tool)
    if include_shell:
        registry.register(SHELL_TOOL)
    return registry
