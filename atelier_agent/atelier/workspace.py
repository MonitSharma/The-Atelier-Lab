"""Approved workspace registry and capability-scoped path resolution.

The registry is deliberately small and local. It is a permission boundary for
Atelier tools, not a claim of OS-level sandboxing: a user who grants shell or
execute access is trusting the local process. Paths are canonicalized before
authorization so symlinks cannot escape an approved root.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from atelier.config import settings

Capability = Literal["read", "write", "execute", "network"]
CAPABILITIES = frozenset({"read", "write", "execute", "network"})
PRIVACY_POLICIES = frozenset({"LOCAL_ONLY", "CLOUD_ALLOWED"})
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class WorkspaceError(ValueError):
    """Raised when a workspace or capability request is invalid."""


@dataclass(frozen=True)
class Workspace:
    name: str
    root: Path
    capabilities: frozenset[str]
    privacy: str = "LOCAL_ONLY"
    attached: bool = False
    system: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "root": str(self.root),
            "capabilities": sorted(self.capabilities),
            "privacy": self.privacy,
            "attached": self.attached,
            "system": self.system,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Workspace:
        try:
            name = str(data["name"])
            root = Path(str(data["root"])).expanduser().resolve()
            capabilities = frozenset(str(value) for value in data.get("capabilities", []))
            privacy = str(data.get("privacy", "LOCAL_ONLY"))
            attached = bool(data.get("attached", False))
            system = bool(data.get("system", False))
        except (KeyError, TypeError, ValueError) as exc:
            raise WorkspaceError("Invalid workspace registry entry.") from exc
        _validate_name(name)
        _validate_capabilities(capabilities, privacy)
        return cls(name, root, capabilities, privacy, attached, system)


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    workspace: Workspace


@dataclass(frozen=True)
class WorkspaceContext:
    """Immutable context passed to a tool execution scope."""

    active: Workspace
    attached: tuple[Workspace, ...]

    def resolve(self, raw_path: str, capability: Capability = "read") -> ResolvedPath:
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise WorkspaceError("A non-empty path is required.")
        requested = Path(raw_path).expanduser()
        base = self.active.root if not requested.is_absolute() else Path(os.sep)
        candidate = (base / requested).resolve(strict=False)

        # Longest matching root wins when approved workspaces are nested.
        owners = [workspace for workspace in self.attached if _inside(candidate, workspace.root)]
        if not owners:
            raise WorkspaceError(
                f"Path is outside all approved workspaces: {raw_path}. "
                "Attach the containing root with `atelier workspace add`."
            )
        owner = max(
            owners,
            key=lambda workspace: (
                len(workspace.root.parts),
                workspace.name == self.active.name,
            ),
        )
        if capability not in owner.capabilities:
            raise WorkspaceError(
                f"Workspace '{owner.name}' does not grant '{capability}' access."
            )
        if capability == "network":
            self.require_network(owner)
        return ResolvedPath(candidate, owner)

    def require_network(self, workspace: Workspace | None = None) -> None:
        owner = workspace or self.active
        if "network" not in owner.capabilities:
            raise WorkspaceError(f"Workspace '{owner.name}' does not grant 'network' access.")
        if owner.privacy != "CLOUD_ALLOWED":
            raise WorkspaceError(
                f"Workspace '{owner.name}' is LOCAL_ONLY; network access is disabled."
            )


_CURRENT_CONTEXT: ContextVar[WorkspaceContext | None] = ContextVar(
    "atelier_workspace_context", default=None
)


def current_workspace_context() -> WorkspaceContext | None:
    return _CURRENT_CONTEXT.get()


@contextmanager
def workspace_scope(context: WorkspaceContext | None) -> Iterator[None]:
    token = _CURRENT_CONTEXT.set(context)
    try:
        yield
    finally:
        _CURRENT_CONTEXT.reset(token)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_name(name: str) -> None:
    if not _NAME_RE.fullmatch(name):
        raise WorkspaceError(
            "Workspace names must be 1–64 characters of letters, numbers, '.', '_' or '-'."
        )


def _validate_capabilities(capabilities: frozenset[str], privacy: str) -> None:
    unknown = capabilities - CAPABILITIES
    if unknown:
        raise WorkspaceError(f"Unknown workspace capabilities: {', '.join(sorted(unknown))}.")
    if privacy not in PRIVACY_POLICIES:
        raise WorkspaceError("Privacy policy must be LOCAL_ONLY or CLOUD_ALLOWED.")
    if "network" in capabilities and privacy != "CLOUD_ALLOWED":
        raise WorkspaceError("Network capability requires the CLOUD_ALLOWED privacy policy.")


class WorkspaceManager:
    """Persist and activate explicitly approved workspace roots."""

    VERSION = 1

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = Path(registry_path or settings.workspace_registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._workspaces: dict[str, Workspace] = {}
        self._active_name: str | None = None
        self._load()

    def _load(self) -> None:
        if not self.registry_path.exists():
            self._install_default_workspace()
            self._save()
            return
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
            entries = payload.get("workspaces", [])
            # Keep approved roots even when they are temporarily unavailable
            # (for example, an unmounted external drive).  Dropping them here
            # and saving later would silently destroy the user's approvals.
            self._workspaces = {
                workspace.name: workspace
                for workspace in (Workspace.from_dict(item) for item in entries)
            }
            active = payload.get("active")
            self._active_name = active if active in self._workspaces else None
        except (OSError, json.JSONDecodeError, TypeError, WorkspaceError) as exc:
            raise WorkspaceError(f"Could not read workspace registry: {self.registry_path}") from exc

        if not self._workspaces:
            self._install_default_workspace()
            self._save()

    def _install_default_workspace(self) -> None:
        root = settings.root.resolve()
        workspace = Workspace(
            name="atelier",
            root=root,
            # The source checkout is readable by default, but must never be a
            # writable trust root merely because Atelier is running elsewhere.
            # Projects that need edits must be explicitly approved below.
            capabilities=frozenset({"read"}),
            privacy="LOCAL_ONLY",
            attached=True,
            system=True,
        )
        self._workspaces = {workspace.name: workspace}
        self._active_name = workspace.name

    def _save(self) -> None:
        payload = {
            "version": self.VERSION,
            "active": self._active_name,
            "workspaces": [workspace.to_dict() for workspace in self._workspaces.values()],
            "updated_at": datetime.now(UTC).isoformat(),
        }
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{self.registry_path.name}.",
            dir=str(self.registry_path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
                handle.write("\n")
            os.replace(temp_name, self.registry_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def list(self) -> list[Workspace]:
        return sorted(self._workspaces.values(), key=lambda item: item.name)

    def get(self, name: str) -> Workspace:
        try:
            return self._workspaces[name]
        except KeyError as exc:
            raise WorkspaceError(f"Unknown workspace: {name}") from exc

    def add(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        capabilities: set[str] | frozenset[str] | None = None,
        privacy: str = "LOCAL_ONLY",
    ) -> Workspace:
        root = Path(path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise WorkspaceError(f"Workspace root must be an existing directory: {path}")
        if root == Path(root.anchor):
            raise WorkspaceError("The filesystem root cannot be an approved workspace.")
        workspace_name = name or root.name or "workspace"
        _validate_name(workspace_name)
        if workspace_name in self._workspaces:
            raise WorkspaceError(f"Workspace already exists: {workspace_name}")
        if any(existing.root == root and not existing.system for existing in self._workspaces.values()):
            raise WorkspaceError(f"Workspace root is already approved: {root}")
        resolved_capabilities = frozenset(capabilities or {"read"})
        _validate_capabilities(resolved_capabilities, privacy)
        workspace = Workspace(workspace_name, root, resolved_capabilities, privacy, attached=False)
        self._workspaces[workspace_name] = workspace
        self._save()
        return workspace

    def open(self, name: str) -> Workspace:
        workspace = self.get(name)
        if not workspace.root.exists() or not workspace.root.is_dir():
            raise WorkspaceError(
                f"Workspace '{name}' is unavailable because its root is not mounted: "
                f"{workspace.root}"
            )
        updated = Workspace(
            workspace.name, workspace.root, workspace.capabilities,
            workspace.privacy, attached=True, system=workspace.system,
        )
        self._workspaces[name] = updated
        self._active_name = name
        self._save()
        return updated

    def activate_directory(
        self,
        path: str | Path,
        *,
        capabilities: set[str] | frozenset[str] | None = None,
        privacy: str = "LOCAL_ONLY",
    ) -> Workspace:
        """Use a directory as the active CLI workspace, creating it if needed.

        This makes the normal terminal experience match repository agents:
        launching Atelier from a directory scopes relative paths to that
        directory. Network access is never granted automatically.
        """
        root = Path(path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise WorkspaceError(f"Workspace root must be an existing directory: {path}")
        matches = [
            workspace for workspace in self._workspaces.values()
            if workspace.root.exists() and workspace.root.is_dir() and _inside(root, workspace.root)
        ]
        if matches:
            return self.open(max(
                matches,
                key=lambda workspace: (len(workspace.root.parts), not workspace.system),
            ).name)
        existing = next((workspace for workspace in self._workspaces.values() if workspace.root == root), None)
        if existing is not None:
            return self.open(existing.name)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", root.name).strip("-")[:32] or "workspace"
        digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:10]
        name = f"cwd-{safe_name}-{digest}"
        workspace = self.add(
            root,
            name=name,
            capabilities=capabilities or {"read"},
            privacy=privacy,
        )
        return self.open(workspace.name)

    def close(self, name: str) -> Workspace:
        workspace = self.get(name)
        updated = Workspace(
            workspace.name, workspace.root, workspace.capabilities,
            workspace.privacy, attached=False, system=workspace.system,
        )
        self._workspaces[name] = updated
        if self._active_name == name:
            attached = [item for item in self._workspaces.values() if item.attached]
            self._active_name = attached[0].name if attached else None
        self._save()
        return updated

    def active(self) -> Workspace:
        if self._active_name is None or self._active_name not in self._workspaces:
            raise WorkspaceError("No workspace is open. Run `atelier workspace open NAME`.")
        workspace = self._workspaces[self._active_name]
        if not workspace.attached:
            raise WorkspaceError("The active workspace is closed.")
        if not workspace.root.exists() or not workspace.root.is_dir():
            raise WorkspaceError(
                f"The active workspace '{workspace.name}' is unavailable because its "
                f"root is not mounted: {workspace.root}"
            )
        return workspace

    def context(self) -> WorkspaceContext:
        attached = tuple(
            item for item in self._workspaces.values()
            if item.attached and item.root.exists() and item.root.is_dir()
        )
        active = self.active()
        return WorkspaceContext(active=active, attached=attached)


def get_workspace_manager() -> WorkspaceManager:
    return WorkspaceManager()
