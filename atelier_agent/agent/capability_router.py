"""Deterministic capability-first routing for Atelier tasks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from agent.router import Router
from atelier.config import settings
from atelier.workspace import WorkspaceContext

Domain = Literal["paper", "code", "data", "vision", "research", "quantum", "optimization", "general"]

_DOMAIN_HINTS: dict[Domain, tuple[str, ...]] = {
    "code": ("repo", "repository", "code", "bug", "test", "refactor", "function", "script", "python", "rust"),
    "data": ("csv", "json", "parquet", "sqlite", "spreadsheet", "dataframe", "dataset", "missing values", "schema"),
    "vision": ("image", "figure", "diagram", "screenshot", "scan", "ocr", "visual", "table image"),
    "quantum": ("quantum", "qiskit", "qubit", "circuit", "transpile", "backend"),
    "optimization": ("optimization", "optimisation", "qubo", "milp", "mip", "linear program", "solver", "constraint"),
    "paper": ("paper", "pdf", "abstract", "methodology", "results section", "characterize", "summarize"),
    "research": ("research", "literature", "citation", "related work", "arxiv", "doi", "crossref"),
    "general": (),
}


@dataclass(frozen=True)
class RouteDecision:
    domain: Domain
    workflow: str
    role: str
    model: str
    difficulty: str
    modality: str
    tools: tuple[str, ...]
    privacy: str
    context_chars: int
    context_budget: int
    use_memory: bool
    requires_network: bool
    abstain: bool
    reason: str
    escalation_conditions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CapabilityRouter:
    """Choose a workflow and cheapest capable role without a model call."""

    def __init__(self, backend: str = "auto") -> None:
        self._difficulty_router = Router(backend=backend)

    @staticmethod
    def _domain(task: str) -> Domain:
        lowered = task.lower()
        scored = {
            domain: sum(1 for hint in hints if hint in lowered)
            for domain, hints in _DOMAIN_HINTS.items()
            if domain != "general"
        }
        return max(scored, key=scored.get) if scored and max(scored.values()) else "general"

    def decide(
        self,
        task: str,
        *,
        workspace: WorkspaceContext | None = None,
        context_chars: int | None = None,
        memory_available: bool = True,
    ) -> RouteDecision:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("A non-empty task is required.")
        domain = self._domain(task)
        difficulty = self._difficulty_router.classify(task)
        lowered = task.lower()
        privacy = workspace.active.privacy if workspace else "LOCAL_ONLY"
        explicit_network = any(term in lowered for term in ("search the web", "search online", "internet", "doi", "arxiv", "crossref"))
        network_blocked = explicit_network and privacy != "CLOUD_ALLOWED"
        chars = context_chars if context_chars is not None else len(task)

        role = "worker"
        workflow = "general"
        modality = "text"
        tools: tuple[str, ...] = ("search_notes",)
        use_memory = False
        escalations: list[str] = []
        reason = "Use the cheapest local text workflow."

        if domain == "code":
            role, workflow = "coder", "code_fix"
            tools = ("repo_inspect", "repo_map", "read_file", "edit_file", "ast_edit", "test_runner")
            reason = "Repository work benefits from the benchmarked coder and certified build workflow."
            escalations.append("escalate to brain if the coder cannot produce a green certificate")
        elif domain == "paper":
            role, workflow = ("heavy", "paper_deep_read") if difficulty == "hard" else ("worker", "paper_fast")
            tools = ("search_notes", "read_file")
            use_memory = memory_available
            reason = "Use deterministic extraction/retrieval first, then increase reasoning only for deep reading."
            escalations.append("escalate to heavy if extraction quality or evidence coverage is insufficient")
        elif domain == "research":
            role, workflow, use_memory = "brain", "research_verify", memory_available
            tools = ("search_notes", "search", "read_file")
            reason = "Research verification needs provenance-aware retrieval and explicit network policy."
            escalations.append("abstain from external lookup when LOCAL_ONLY blocks the requested source")
        elif domain == "vision":
            role, workflow, modality = "heavy", "figure_inspect", "image_or_document"
            tools = ("read_file", "search_notes")
            reason = "The installed heavy model is the only configured local multimodal-capable role."
            escalations.append("request a vision-capable input or abstain if no visual artifact is attached")
        elif domain == "data":
            role, workflow = "brain", "data_analyze"
            tools = ("repo_inspect", "read_file", "code_exec", "test_runner")
            reason = "Deterministic file profiling should precede model-assisted analysis."
            escalations.append("escalate to heavy for data that exceeds the context budget")
        elif domain == "quantum":
            role, workflow = "brain", "quantum_analyze"
            tools = ("read_file", "code_exec", "search_notes")
            reason = "Quantum results must come from deterministic circuit tools, with the model explaining them."
            escalations.append("escalate to heavy for large research synthesis after tool results are available")
        elif domain == "optimization":
            role, workflow = "brain", "optimization_validate"
            tools = ("read_file", "code_exec", "search_notes")
            reason = "Solvers and feasibility checks should produce the facts before reasoning."
            escalations.append("abstain if a solver certificate cannot be produced")
        elif difficulty == "hard":
            role = "brain"
            tools = ("search_notes", "read_file", "calculator")
            reason = "The generic task is long or cross-cutting, so use the reasoning role."

        if chars > settings.max_context_chars:
            escalations.append("summarize or retrieve selectively before exceeding the context budget")
        if network_blocked:
            return RouteDecision(
                domain=domain, workflow=workflow, role=role, model="", difficulty=difficulty,
                modality=modality, tools=tools, privacy=privacy, context_chars=chars,
                context_budget=settings.max_context_chars, use_memory=use_memory,
                requires_network=True, abstain=True,
                reason="The requested external lookup conflicts with LOCAL_ONLY privacy.",
                escalation_conditions=tuple(escalations),
            )

        model = getattr(settings, f"{role}_model", "")
        return RouteDecision(
            domain=domain, workflow=workflow, role=role, model=model,
            difficulty=difficulty, modality=modality, tools=tools, privacy=privacy,
            context_chars=chars, context_budget=settings.max_context_chars,
            use_memory=use_memory, requires_network=explicit_network,
            abstain=False, reason=reason,
            escalation_conditions=tuple(escalations),
        )
