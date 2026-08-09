"""Explicit, local handoff bundles for frontier-model workflows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_markdown(self) -> str:
        sections = [f"# Atelier handoff → {self.target}", "", f"Task\n\n{self.task}"]
        for title, values in (("Selected context", self.selected_context), ("Evidence", self.evidence), ("Constraints", self.constraints)):
            sections.extend(["", title, "", *[f"- {value}" for value in values]])
        sections.extend(["", "Requested output", "", self.requested_output,
                          "", f"External transfer approved: {self.approved_for_external_transfer}"])
        return "\n".join(sections) + "\n"


def create_handoff(target: str, task: str, *, selected_context: list[str] | None = None,
                   evidence: list[str] | None = None, constraints: list[str] | None = None,
                   requested_output: str = "Return a concise, evidence-grounded result.",
                   approved_for_external_transfer: bool = False) -> HandoffBundle:
    if target not in TARGETS:
        raise ValueError(f"target must be one of: {', '.join(sorted(TARGETS))}")
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task is required")
    if approved_for_external_transfer and not constraints:
        raise ValueError("external transfer approval requires explicit constraints")
    return HandoffBundle(target, task.strip(), tuple(selected_context or ()), tuple(evidence or ()),
                         tuple(constraints or ()), requested_output.strip(), datetime.now(UTC).isoformat(),
                         approved_for_external_transfer)


def export_handoff(bundle: HandoffBundle, path: str | Path, *, markdown: bool = False) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if markdown:
        target.write_text(bundle.to_markdown(), encoding="utf-8")
    else:
        target.write_text(json.dumps(bundle.to_dict(), indent=2) + "\n", encoding="utf-8")
    return target
