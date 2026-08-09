from atelier.workflows import get_workflow, list_workflows
from tools.registry import create_default_registry


def test_workflow_catalog_has_recovery_and_approval_metadata():
    workflows = list_workflows()
    assert {workflow.name for workflow in workflows} >= {"paper_fast", "code_fix", "research_verify", "quantum_analyze", "optimization_validate"}
    assert all(workflow.steps and workflow.recovery for workflow in workflows)
    assert get_workflow("code_fix").approval_gate


def test_science_and_research_tools_are_registered():
    names = {tool.name for tool in create_default_registry().list_tools()}
    assert {"research_lookup", "quantum_inspect", "optimization_validate"} <= names
