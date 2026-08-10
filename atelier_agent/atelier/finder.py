"""Opt-in Finder/Shortcuts bridge actions.

These functions create explicit action plans. They do not install watchers or
index files until the user invokes a concrete command.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import shutil

from atelier.workspace import WorkspaceManager, get_workspace_manager
from files.artifacts import profile_path
from atelier.config import settings

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


def execute_finder_action(
    action: str,
    path: str | Path,
    *,
    manager: WorkspaceManager | None = None,
    task: str | None = None,
) -> dict[str, Any]:
    """Execute one user-invoked Finder action through the shared service."""
    manager = manager or get_workspace_manager()
    resolved = manager.context().resolve(str(path), "read").path
    from atelier.service import AtelierService

    service = AtelierService(manager=manager)
    if action == "explain_file":
        return {"status": "success", "action": action, "result": service.profile(str(path))}
    if action == "characterize_paper":
        if resolved.suffix.lower() != ".pdf":
            raise ValueError("characterize_paper requires a PDF")
        return {"status": "success", "action": action, "result": service.paper_action("characterize", str(path))}
    if action == "send_to_atelier":
        return {"status": "success", "action": action,
                "result": service.chat(task or f"Explain the selected file: {resolved.name}", input_data={"path": str(path)})}
    if action == "add_to_library":
        settings.ensure_dirs()
        digest = hashlib.sha256(resolved.read_bytes()).hexdigest()[:12]
        target = settings.corpus_dir / f"{resolved.stem}-{digest}{resolved.suffix.lower()}"
        if not target.exists():
            shutil.copy2(resolved, target)
        return {"status": "success", "action": action, "source": str(resolved),
                "library_path": str(target), "indexed": False,
                "next": "Run `atelier ingest` to embed the selected file."}
    raise ValueError(f"Unknown Finder action: {action}")
