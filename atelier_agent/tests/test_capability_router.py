from agent.capability_router import CapabilityRouter
from eval.capability_routing import run_capability_eval


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


def test_deep_research_routes_to_bounded_network_workflow() -> None:
    decision = CapabilityRouter(backend="heuristic").decide("Do deep research on reliable local AI agents")
    assert decision.domain == "research"
    assert decision.workflow == "research_deep"
    assert decision.requires_network
    assert decision.abstain
    assert "web_search" in decision.tools
    assert "web_fetch" in decision.tools


def test_paper_route_uses_memory() -> None:
    decision = CapabilityRouter(backend="heuristic").decide("Summarize this paper's methodology")
    assert decision.domain == "paper"
    assert decision.use_memory


def test_upsc_study_route_uses_preparation_track() -> None:
    decision = CapabilityRouter(backend="heuristic").decide(
        "Create a UPSC mains answer on polity and cite the indexed current-affairs notes"
    )
    assert decision.domain == "study"
    assert decision.workflow == "study_coach"
    assert decision.role == "brain"
    assert decision.use_memory


def test_upsc_recall_route_uses_worker_for_short_questions() -> None:
    decision = CapabilityRouter(backend="heuristic").decide(
        "Which indexed prelims notes cover the Finance Commission?"
    )
    assert decision.domain == "study"
    assert decision.workflow == "study_retrieve"
    assert decision.role == "worker"


def test_frozen_capability_routing_evaluation_passes():
    report = run_capability_eval()
    assert report["cases"] == 17
    assert report["successes"] == 17
    assert report["domain_accuracy"] == 1.0
    assert report["workflow_accuracy"] == 1.0
    assert report["abstention_accuracy"] == 1.0
