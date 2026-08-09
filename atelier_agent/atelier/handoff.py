"""Explicit, local handoff bundles for frontier-model workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from atelier.security import redact_secrets
from atelier.workspace import WorkspaceManager, get_workspace_manager

TARGETS = frozenset({"claude", "codex", "gemini"})


@dataclass(frozen=True)
class HandoffBundle:
    target: str
    task: str
    selected_context: tuple[str, ...]
    evidence: tuple[str, ...]
    constraints: tuple[str, ...]
    requested_output: str
    created_at: str
    approved_for_external_transfer: bool = False
    selected_file_contents: dict[str, str] | None = None
    secrets_redacted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        sections = [f"# Atelier handoff → {self.target}", "", f"Task\n\n{self.task}"]
        for title, values in (("Selected context", self.selected_context), ("Evidence", self.evidence), ("Constraints", self.constraints)):
            sections.extend(["", title, "", *[f"- {value}" for value in values]])
        if self.selected_file_contents:
            sections.extend(["", "Selected file contents", ""])
            for path, content in self.selected_file_contents.items():
                sections.extend([f"### {path}", "", "```text", content, "```"])
        sections.extend(["", "Requested output", "", self.requested_output,
                          "", f"External transfer approved: {self.approved_for_external_transfer}"])
        return "\n".join(sections) + "\n"


def create_handoff(target: str, task: str, *, selected_context: list[str] | None = None,
                   evidence: list[str] | None = None, constraints: list[str] | None = None,
                   requested_output: str = "Return a concise, evidence-grounded result.",
                   approved_for_external_transfer: bool = False,
                   manager: WorkspaceManager | None = None,
                   include_file_contents: bool = False) -> HandoffBundle:
    if target not in TARGETS:
        raise ValueError(f"target must be one of: {', '.join(sorted(TARGETS))}")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task is required")
    if approved_for_external_transfer and not constraints:
        raise ValueError("external transfer approval requires explicit constraints")
    redacted = False

    def safe(value: str) -> str:
        nonlocal redacted
        cleaned, changed = redact_secrets(value)
        redacted = redacted or changed
        return cleaned

    context_values = [safe(str(value)) for value in (selected_context or ())]
    evidence_values = [safe(str(value)) for value in (evidence or ())]
    constraint_values = [safe(str(value)) for value in (constraints or ())]
    contents: dict[str, str] = {}
    if include_file_contents:
        workspace_manager = manager or get_workspace_manager()
        for raw_path in context_values:
            resolved = workspace_manager.context().resolve(raw_path, "read").path
            if not resolved.is_file():
                raise ValueError(f"Selected handoff context is not a file: {raw_path}")
            text, changed = redact_secrets(resolved.read_text(encoding="utf-8", errors="replace")[:100_000])
            redacted = redacted or changed
            contents[str(resolved)] = text
    return HandoffBundle(target, safe(task.strip()), tuple(context_values), tuple(evidence_values),
                         tuple(constraint_values), safe(requested_output.strip()), datetime.now(UTC).isoformat(),
                         approved_for_external_transfer, contents or None, redacted)


def export_handoff(bundle: HandoffBundle, path: str | Path, *, markdown: bool = False) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if markdown:
        target.write_text(bundle.to_markdown(), encoding="utf-8")
    else:
        target.write_text(json.dumps(bundle.to_dict(), indent=2) + "\n", encoding="utf-8")
    return target
