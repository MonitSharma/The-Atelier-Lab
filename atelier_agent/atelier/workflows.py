"""Typed, inspectable workflow specifications.

Execution is intentionally separate from the catalog. Later service/UI layers
can execute these specs while keeping their checkpoints and approval gates
visible to the user.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WorkflowSpec:
    name: str
    purpose: str
    steps: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    approval_gate: str
    recovery: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


WORKFLOWS: tuple[WorkflowSpec, ...] = (
    WorkflowSpec("paper_fast", "Characterize one paper quickly", ("identify", "extract", "characterize", "cite"), ("read",), "none", "return partial evidence"),
    WorkflowSpec("paper_deep_read", "Build a cited, section-aware paper analysis", ("characterize", "retrieve", "inspect figures", "synthesize", "verify citations"), ("read",), "human review before export", "preserve evidence and retry failed extraction"),
    WorkflowSpec("paper_compare", "Compare papers against explicit dimensions", ("characterize each", "align claims", "compare evidence", "report gaps"), ("read",), "human review before conclusion", "mark missing dimensions"),
    WorkflowSpec("figure_inspect", "Extract and interpret scientific figure evidence", ("locate pages", "render evidence", "interpret visual", "cite pages"), ("read",), "human review before interpretation", "preserve page evidence and retry rendering"),
    WorkflowSpec("repo_inspect", "Understand a repository deterministically", ("inspect", "map symbols", "find tests", "report state"), ("read",), "none", "return partial profile"),
    WorkflowSpec("code_fix", "Make and verify a repository change", ("inspect", "plan", "baseline tests", "edit", "targeted tests", "regression", "certificate"), ("read", "write", "execute"), "approval before destructive rollback", "checkpoint and optionally rollback"),
    WorkflowSpec("data_analyze", "Profile and analyze a structured artifact", ("profile", "validate", "summarize", "cite inputs"), ("read",), "human review before write/export", "retain profile and warnings"),
    WorkflowSpec("research_verify", "Verify an explicit external research claim", ("query approved source", "record provenance", "compare local evidence", "report uncertainty"), ("read", "network"), "human review before download or publication", "return provenance and retry metadata"),
    WorkflowSpec("quantum_analyze", "Inspect and validate a quantum circuit", ("parse", "count resources", "transpile/simulate if available", "report limits"), ("read",), "human review before backend execution", "preserve parser and dependency evidence"),
    WorkflowSpec("optimization_validate", "Validate a proposed optimization solution", ("parse problem", "check feasibility", "compute objective", "compare solutions"), ("read",), "human review before solver/backend run", "return failed checks without mutation"),
)


def list_workflows() -> list[WorkflowSpec]:
    return list(WORKFLOWS)


def get_workflow(name: str) -> WorkflowSpec:
    for workflow in WORKFLOWS:
        if workflow.name == name:
            return workflow
    raise KeyError(f"Unknown workflow: {name}")
