"""Opt-in Finder/Shortcuts bridge actions.

These functions create explicit action plans. They do not install watchers or
index files until the user invokes a concrete command.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from atelier.workspace import WorkspaceManager, get_workspace_manager
from files.artifacts import profile_path

FINDER_ACTIONS = ("send_to_atelier", "add_to_library", "characterize_paper", "explain_file")


def prepare_finder_action(action: str, path: str | Path, manager: WorkspaceManager | None = None) -> dict[str, Any]:
    if action not in FINDER_ACTIONS:
        raise ValueError(f"Unknown Finder action: {action}")
    manager = manager or get_workspace_manager()
    resolved = manager.context().resolve(str(path), "read").path
    result: dict[str, Any] = {
        "status": "planned", "action": action, "path": str(resolved),
        "workspace": manager.context().active.name,
        "privacy": manager.context().active.privacy,
        "watching": False, "requires_user_invocation": True,
    }
    if action == "explain_file":
        result["profile"] = profile_path(resolved).to_dict()
    elif action == "characterize_paper":
        if resolved.suffix.lower() != ".pdf":
            raise ValueError("characterize_paper requires a PDF")
        result["next"] = "atelier paper PATH"
    elif action == "add_to_library":
        result["next"] = "atelier ingest PATH"
    else:
        result["next"] = "atelier ask or atelier agent with the selected path"
    return result
