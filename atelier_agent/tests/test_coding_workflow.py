from pathlib import Path

from agent.coding_workflow import (
    BuildWorkflow,
    Checkpoint,
    _tool_names,
)
from agent.react import AgentResult
from repo.inspector import RepositoryInspector


def test_checkpoint_restores_edits_and_removes_new_files(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("return 1\n", encoding="utf-8")
    inspector = RepositoryInspector.for_path(tmp_path)
    checkpoint = Checkpoint.capture(tmp_path, inspector)

    source.write_text("return 2\n", encoding="utf-8")
    (tmp_path / "new.py").write_text("created\n", encoding="utf-8")
    result = checkpoint.restore()

    assert source.read_text(encoding="utf-8") == "return 1\n"
    assert not (tmp_path / "new.py").exists()
    assert result["restored"] == ["main.py"]
    assert result["removed"] == ["new.py"]


def test_tool_names_extracts_only_model_tool_decisions() -> None:
    result = AgentResult(
        answer="done",
        success=True,
        steps=2,
        trace=[
            {"decision": {"type": "tool_call", "tool": "repo_map"}},
            {"decision": {"type": "final", "answer": "done"}},
        ],
    )
    assert _tool_names(result) == ["repo_map"]


def test_workflow_emits_accepted_certificate(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("value = 1\n", encoding="utf-8")

    def fake_tests(_arguments):
        return {"status": "success", "passed_clean": True, "summary": "1 passed"}

    class FakeAgent:
        def __init__(self, *_args, **_kwargs):
            pass

        def run(self, _prompt):
            return AgentResult(
                answer="verified",
                success=True,
                steps=3,
                trace=[
                    {"decision": {"tool": "repo_map"}},
                    {"decision": {"tool": "edit_file"}},
                    {"decision": {"tool": "test_runner"}},
                ],
            )

    monkeypatch.setattr("agent.coding_workflow.run_tests", fake_tests)
    workflow = BuildWorkflow(tmp_path, agent_factory=FakeAgent)
    monkeypatch.setattr(workflow, "_diff_review", lambda _inspector: {"passed": True, "files": [], "stat": ""})
    result = workflow.run("make the change", escalation_role=None)

    assert result.accepted
    assert result.certificate.attempts == 1
    assert [stage.name for stage in result.certificate.stages].count("certificate") == 1
