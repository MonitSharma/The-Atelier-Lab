from agent.capability_router import CapabilityRouter


def test_code_routes_to_benchmarked_coder_workflow() -> None:
    decision = CapabilityRouter(backend="heuristic").decide("Fix the failing tests in this repository")
    assert decision.domain == "code"
    assert decision.workflow == "code_fix"
    assert decision.role == "coder"
    assert "test_runner" in decision.tools
    assert not decision.abstain


def test_local_only_external_lookup_abstains() -> None:
    decision = CapabilityRouter(backend="heuristic").decide("Search the web for the latest DOI")
    assert decision.requires_network
    assert decision.abstain
    assert decision.model == ""


def test_paper_route_uses_memory() -> None:
    decision = CapabilityRouter(backend="heuristic").decide("Summarize this paper's methodology")
    assert decision.domain == "paper"
    assert decision.use_memory
