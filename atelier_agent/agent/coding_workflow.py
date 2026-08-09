"""Typed, evidence-producing coding workflow built on the ReAct primitive.

The ReAct loop remains responsible for model/tool interaction. This module is
the workflow boundary around it: deterministic inspection and tests happen
outside the model, edits are checkpointed, retries can escalate to a larger
role, and the final result is a certificate rather than an unverified answer.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from agent.react import AgentResult, ReActAgent
from atelier.workspace import WorkspaceContext, workspace_scope
from repo.inspector import RepositoryInspector
from tools.registry import ToolRegistry, create_default_registry
from tools.test_runner import run_tests

StageName = Literal[
    "inspect", "plan", "identify_files", "baseline_tests", "edit",
    "targeted_tests", "regression_tests", "diff_review", "certificate",
]
StageStatus = Literal["passed", "failed", "skipped"]


@dataclass(frozen=True)
class StageEvidence:
    name: StageName
    status: StageStatus
    detail: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Checkpoint:
    """In-memory pre-edit snapshot for a single workflow attempt."""

    root: Path
    files: dict[str, bytes]
    baseline_dirty: frozenset[str]
    skipped_files: tuple[str, ...] = ()
    created_at: str = ""

    @classmethod
    def capture(cls, root: Path, inspector: RepositoryInspector) -> "Checkpoint":
        before: dict[str, bytes] = {}
        skipped: list[str] = []
        for path in inspector._files()[0]:  # bounded by the inspector's safety cap
            rel = path.relative_to(root).as_posix()
            try:
                size = path.stat().st_size
                if size > 20 * 1024 * 1024:
                    skipped.append(rel)
                    continue
                before[rel] = path.read_bytes()
            except OSError:
                skipped.append(rel)
        status = inspector.git_status()
        dirty = frozenset(str(row.get("path", "")) for row in status.get("entries", []))
        return cls(
            root=root,
            files=before,
            baseline_dirty=dirty,
            skipped_files=tuple(sorted(skipped)),
            created_at=datetime.now(UTC).isoformat(),
        )

    def restore(self) -> dict[str, Any]:
        """Restore clean baseline files and remove new clean files.

        Pre-existing dirty paths are intentionally preserved. This makes an
        opt-in rollback safe to use in a user's already-active worktree.
        """
        restored: list[str] = []
        removed: list[str] = []
        preserved_dirty: list[str] = []
        current: dict[str, Path] = {}
        for directory, dirs, names in os.walk(self.root):
            dirs[:] = [name for name in dirs if name not in {".git", ".venv", "node_modules"}]
            for name in names:
                path = Path(directory) / name
                if path.is_symlink():
                    continue
                current[path.relative_to(self.root).as_posix()] = path

        for rel, content in self.files.items():
            if rel in self.baseline_dirty:
                preserved_dirty.append(rel)
                continue
            path = self.root / rel
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
                restored.append(rel)
            except OSError:
                preserved_dirty.append(rel)

        for rel, path in current.items():
            if rel in self.files or rel in self.baseline_dirty or rel in self.skipped_files:
                continue
            try:
                path.unlink()
                removed.append(rel)
            except OSError:
                preserved_dirty.append(rel)
        return {
            "restored": sorted(restored),
            "removed": sorted(removed),
            "preserved_dirty": sorted(set(preserved_dirty)),
            "skipped_files": list(self.skipped_files),
        }


@dataclass(frozen=True)
class BuildCertificate:
    accepted: bool
    role: str
    model: str | None
    repository: str
    attempts: int
    escalated: bool
    stages: tuple[StageEvidence, ...]
    changed_files: tuple[str, ...]
    test_result: dict[str, Any]
    diff_review: dict[str, Any]
    rollback: dict[str, Any] | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stages"] = [stage.to_dict() for stage in self.stages]
        return payload


@dataclass(frozen=True)
class BuildWorkflowResult:
    certificate: BuildCertificate
    agent_results: tuple[AgentResult, ...]
    profile: dict[str, Any]

    @property
    def accepted(self) -> bool:
        return self.certificate.accepted


def _digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _changed_files(root: Path, checkpoint: Checkpoint, inspector: RepositoryInspector) -> list[str]:
    changed: set[str] = set()
    git_files = inspector.git_diff().get("files", [])
    changed.update(str(row.get("path", "")) for row in git_files if row.get("path"))
    for rel, content in checkpoint.files.items():
        path = root / rel
        if not path.exists() or _digest(path) != hashlib.sha256(content).hexdigest():
            changed.add(rel)
    for directory, _, names in os.walk(root):
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            if rel not in checkpoint.files:
                changed.add(rel)
    return sorted(changed)


def _tool_names(result: AgentResult) -> list[str]:
    names: list[str] = []
    for entry in result.trace:
        decision = entry.get("decision")
        if isinstance(decision, dict) and isinstance(decision.get("tool"), str):
            names.append(decision["tool"])
    return names


def _test_passed(result: dict[str, Any]) -> bool:
    return bool(result.get("status") == "success" and result.get("passed_clean"))


class BuildWorkflow:
    """Run a test-certified coding task with optional model escalation."""

    def __init__(
        self,
        root: str | Path,
        *,
        workspace: WorkspaceContext | None = None,
        registry: ToolRegistry | None = None,
        agent_factory: Callable[..., ReActAgent] = ReActAgent,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.workspace = workspace
        self.registry = registry or create_default_registry(workspace=workspace)
        self.agent_factory = agent_factory

    def _run_tests(self) -> dict[str, Any]:
        with workspace_scope(self.workspace):
            return run_tests({"path": str(self.root)})

    def _diff_review(self, inspector: RepositoryInspector) -> dict[str, Any]:
        check = subprocess.run(
            ["git", "diff", "--check"], cwd=self.root, capture_output=True,
            text=True, timeout=20, check=False,
        )
        diff = inspector.git_diff()
        return {
            "passed": check.returncode == 0,
            "git_diff_check": check.stdout.strip() + check.stderr.strip(),
            "stat": diff.get("stat", ""),
            "files": diff.get("files", []),
        }

    def _attempt(
        self,
        prompt: str,
        *,
        role: str,
        model: str | None,
        max_steps: int,
    ) -> AgentResult:
        agent = self.agent_factory(
            self.registry, role=role, model=model, max_steps=max_steps,
            log=False, use_memory=False,
        )
        return agent.run(prompt)

    def run(
        self,
        goal: str,
        *,
        role: str = "coder",
        model: str | None = None,
        escalation_role: str | None = "brain",
        escalation_model: str | None = None,
        max_steps: int = 14,
        rollback_on_failure: bool = False,
    ) -> BuildWorkflowResult:
        inspector = RepositoryInspector.for_path(self.root)
        profile = inspector.inspect()
        checkpoint = Checkpoint.capture(self.root, inspector)
        stages: list[StageEvidence] = [
            StageEvidence("inspect", "passed", "Deterministic repository profile created.", {
                "file_count": profile["file_count"], "languages": profile["languages"],
            }),
            StageEvidence("plan", "passed", "Agent received the typed coding protocol."),
            StageEvidence("identify_files", "skipped", "Agent evidence is recorded after the attempt."),
        ]
        baseline = self._run_tests()
        stages.append(StageEvidence(
            "baseline_tests", "passed" if _test_passed(baseline) else "failed",
            baseline.get("summary", "No baseline test summary."), baseline,
        ))

        protocol = f"""Complete this coding task in the approved repository `{self.root}`.

Required workflow stages (follow them in order and use the tools):
1. inspect and plan; 2. identify the exact files; 3. run baseline tests;
4. make the smallest compatible edits; 5. run targeted tests after each logical
change; 6. run the complete regression suite; 7. review the diff for accidental
changes; 8. finish only with a concise evidence-based certificate.

User task:
{goal}

Rules: preserve existing tests and public APIs, do not claim success without a
green `test_runner` result, and do not use the shell. The workflow will run an
independent final test and diff review after you finish."""

        attempts: list[AgentResult] = []
        current_role, current_model = role, model
        escalated = False
        rollback_info: dict[str, Any] | None = None
        while True:
            result = self._attempt(protocol, role=current_role, model=current_model, max_steps=max_steps)
            attempts.append(result)
            tools = _tool_names(result)
            stages[2] = StageEvidence(
                "identify_files", "passed" if any(tool in tools for tool in {"repo_map", "repo_inspect", "read_file"}) else "failed",
                "; ".join(sorted(set(tools))), {"tools": tools},
            )
            stages.append(StageEvidence(
                "edit", "passed" if any(tool in tools for tool in {"write_file", "edit_file", "ast_edit"}) else "failed",
                "Edit tool observed." if any(tool in tools for tool in {"write_file", "edit_file", "ast_edit"}) else "No edit tool observed.",
            ))
            stages.append(StageEvidence(
                "targeted_tests", "passed" if "test_runner" in tools else "failed",
                "test_runner was invoked." if "test_runner" in tools else "No test_runner invocation observed.",
            ))
            regression = self._run_tests()
            review = self._diff_review(inspector)
            accepted = bool(result.success and _test_passed(regression) and review["passed"])
            if accepted or not escalation_role or escalated:
                break
            if checkpoint.baseline_dirty:
                # Do not overwrite a user's pre-existing work just to retry.
                break
            rollback_info = checkpoint.restore()
            escalated = True
            current_role, current_model = escalation_role, escalation_model

        changed = _changed_files(self.root, checkpoint, inspector)
        if rollback_on_failure and not accepted and rollback_info is None:
            rollback_info = checkpoint.restore()
            changed = _changed_files(self.root, checkpoint, inspector)
        regression = self._run_tests()
        review = self._diff_review(inspector)
        accepted = bool(attempts[-1].success and _test_passed(regression) and review["passed"])
        stages.append(StageEvidence(
            "regression_tests", "passed" if _test_passed(regression) else "failed",
            regression.get("summary", ""), regression,
        ))
        stages.append(StageEvidence(
            "diff_review", "passed" if review["passed"] else "failed",
            review.get("stat", ""), review,
        ))
        stages.append(StageEvidence(
            "certificate", "passed" if accepted else "failed",
            "Accepted only with a finished agent, green regression tests, and a clean diff check.",
            {"accepted": accepted, "attempts": len(attempts), "changed_files": changed},
        ))
        certificate = BuildCertificate(
            accepted=accepted,
            role=current_role,
            model=current_model,
            repository=str(self.root),
            attempts=len(attempts),
            escalated=escalated,
            stages=tuple(stages),
            changed_files=tuple(changed),
            test_result=regression,
            diff_review=review,
            rollback=rollback_info,
            created_at=datetime.now(UTC).isoformat(),
        )
        return BuildWorkflowResult(certificate, tuple(attempts), profile)
