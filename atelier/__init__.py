"""Atelier — a fully local, zero-cost, dual-mode AI agent.

This package holds cross-cutting concerns (configuration, CLI). The capability
packages live as siblings, mirroring PROJECT.md §5:

    agent/   the ReAct loop, brain client, memory
    tools/   the tool registry and individual tools
    rag/     knowledge mode: ingest -> chunk -> embed -> store -> retrieve
"""

__version__ = "0.1.0"
