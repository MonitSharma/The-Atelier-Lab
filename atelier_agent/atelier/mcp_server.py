"""Expose Atelier's toolbox over the Model Context Protocol (MCP).

This turns the agent's tools — semantic note search, file read/write/edit,
sandboxed code exec, the pytest runner, repo map, memory — into a standard MCP
server that *other* clients can use (Claude Desktop/Code, or any MCP host). The
same registry that powers the local ReAct loop is published verbatim, so there's
one source of truth for tool schemas.

Run it:  ``atelier mcp``  (or ``python -m atelier.mcp_server``). It speaks
JSON-RPC over stdio — point your MCP client's command at it.

Note: stdout is reserved for the protocol, so nothing here prints to stdout.
"""

from __future__ import annotations

import asyncio
import json

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server


def build_server(include_shell: bool = False) -> Server:
    from tools.registry import create_default_registry
    from atelier.workspace import get_workspace_manager

    registry = create_default_registry(
        include_shell=include_shell,
        workspace=get_workspace_manager().context(),
    )
    server: Server = Server("atelier")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(name=t.name, description=t.description, inputSchema=t.input_schema)
            for t in registry.list_tools()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        # Tools are synchronous + local; run off the event loop to stay responsive.
        result = await asyncio.to_thread(registry.execute, name, arguments or {})
        return [types.TextContent(type="text", text=json.dumps(result, default=str))]

    return server


async def run_stdio(include_shell: bool = False) -> None:
    server = build_server(include_shell=include_shell)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main(include_shell: bool = False) -> None:
    asyncio.run(run_stdio(include_shell=include_shell))


if __name__ == "__main__":
    import os

    main(include_shell=os.environ.get("ATELIER_MCP_SHELL") == "1")
