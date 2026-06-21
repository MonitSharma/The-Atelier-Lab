"""ReAct engine tests with a scripted brain (no Ollama needed).

We monkeypatch the model call so the loop is deterministic, then assert the
engine routes tool calls, feeds observations back, reflects on bad output, and
terminates correctly.
"""

import json

import agent.react as react
from agent.react import ReActAgent
from tools.base import Tool
from tools.registry import ToolRegistry


def _echo_tool() -> Tool:
    return Tool(
        name="echo",
        description="Echo back the text.",
        input_schema={"type": "object", "properties": {"text": {"type": "string"}},
                      "required": ["text"]},
        function=lambda args: {"status": "success", "echoed": args.get("text")},
    )


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(_echo_tool())
    return reg


def _script(responses):
    """Return a fake chat() that yields the queued responses in order."""
    queue = list(responses)

    def fake_chat(messages, **kwargs):
        return queue.pop(0)

    return fake_chat


def test_tool_then_final(monkeypatch) -> None:
    monkeypatch.setattr(react, "chat", _script([
        json.dumps({"type": "tool_call", "tool": "echo", "arguments": {"text": "hi"}}),
        json.dumps({"type": "final", "answer": "done: hi"}),
    ]))
    result = ReActAgent(_registry(), log=False).run("say hi")
    assert result.success
    assert result.steps == 2
    assert result.answer == "done: hi"
    # the observation from the tool should be in the trace
    assert result.trace[0]["observation"]["echoed"] == "hi"


def test_reflects_on_bad_json_then_recovers(monkeypatch) -> None:
    monkeypatch.setattr(react, "chat", _script([
        "this is not json",                                   # step 1: bad
        json.dumps({"type": "final", "answer": "recovered"}),  # step 2: good
    ]))
    result = ReActAgent(_registry(), log=False, max_steps=4).run("x")
    assert result.success
    assert result.answer == "recovered"
    assert result.trace[0]["error"]["error_type"] == "invalid_model_output"


def test_unknown_tool_is_observed_not_crashed(monkeypatch) -> None:
    monkeypatch.setattr(react, "chat", _script([
        json.dumps({"type": "tool_call", "tool": "ghost", "arguments": {}}),
        json.dumps({"type": "final", "answer": "ok"}),
    ]))
    result = ReActAgent(_registry(), log=False).run("x")
    assert result.success
    assert result.trace[0]["observation"]["error_type"] == "unknown_tool"


def test_gives_up_after_max_steps(monkeypatch) -> None:
    loop = json.dumps({"type": "tool_call", "tool": "echo", "arguments": {"text": "again"}})
    monkeypatch.setattr(react, "chat", lambda messages, **kw: loop)
    result = ReActAgent(_registry(), log=False, max_steps=3).run("loop forever")
    assert not result.success
    assert result.steps == 3
