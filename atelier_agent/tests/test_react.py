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


def _failing_tool() -> tuple[Tool, dict[str, int]]:
    """A tool that always errors, and counts how often it actually ran."""
    calls = {"n": 0}

    def run(args):
        calls["n"] += 1
        return {"status": "error", "error_type": "boom", "message": "always fails"}

    tool = Tool(name="boom", description="Always fails.",
                input_schema={"type": "object", "properties": {}}, function=run)
    return tool, calls


def test_identical_failing_call_is_not_re_executed(monkeypatch) -> None:
    """A repeated failing call should be answered from the record, not re-run."""
    tool, calls = _failing_tool()
    registry = ToolRegistry()
    registry.register(tool)
    call = json.dumps({"type": "tool_call", "tool": "boom", "arguments": {}})
    monkeypatch.setattr(react, "chat", _script([
        call, call, call,
        json.dumps({"type": "final", "answer": "gave up on boom"}),
    ]))

    result = ReActAgent(registry, log=False, max_steps=6).run("x")

    assert result.success
    assert calls["n"] == 1, "the failing tool should have executed exactly once"
    assert result.trace[1]["observation"]["error_type"] == "repeated_failing_call"
    assert result.trace[2]["repeated_call"] is True


def test_repeated_successful_call_still_executes(monkeypatch) -> None:
    """Only *failing* calls are short-circuited; repetition can be legitimate."""
    call = json.dumps({"type": "tool_call", "tool": "echo", "arguments": {"text": "hi"}})
    monkeypatch.setattr(react, "chat", _script([
        call, call, json.dumps({"type": "final", "answer": "ok"}),
    ]))

    result = ReActAgent(_registry(), log=False, max_steps=5).run("x")

    assert result.success
    assert result.trace[1]["observation"]["echoed"] == "hi"
    assert "repeated_call" not in result.trace[1]


def test_persistent_bad_json_aborts_on_its_own_budget(monkeypatch) -> None:
    """Unparseable output must not silently consume every step."""
    monkeypatch.setattr(react, "chat", lambda messages, **kw: "still not json")

    result = ReActAgent(_registry(), log=False, max_steps=20, parse_error_budget=3).run("x")

    assert not result.success
    assert result.failure_reason == "parse_error_budget"
    assert result.steps == 3, "should stop at the parse budget, not at max_steps"


def test_step_budget_exhaustion_is_reported_distinctly(monkeypatch) -> None:
    loop = json.dumps({"type": "tool_call", "tool": "echo", "arguments": {"text": "again"}})
    monkeypatch.setattr(react, "chat", lambda messages, **kw: loop)

    result = ReActAgent(_registry(), log=False, max_steps=3).run("loop forever")

    assert result.failure_reason == "step_budget"


def test_context_is_pruned_to_a_sliding_window(monkeypatch) -> None:
    """Long runs must not grow the prompt without bound."""
    seen_lengths = []

    def fake_chat(messages, **kwargs):
        seen_lengths.append(len(messages))
        return json.dumps({"type": "tool_call", "tool": "echo",
                           "arguments": {"text": f"step{len(seen_lengths)}"}})

    monkeypatch.setattr(react, "chat", fake_chat)
    agent = ReActAgent(_registry(), log=False, max_steps=12, history_pairs=3)
    agent.run("x")

    # system + goal + elision summary + 3 exchanges (2 messages each) = 9
    assert max(seen_lengths) == 9
    assert seen_lengths[-1] == 9


def test_pruning_tells_the_model_that_history_was_dropped() -> None:
    agent = ReActAgent(_registry(), log=False, history_pairs=2)
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "goal"}]
    for i in range(6):
        messages.append({"role": "assistant", "content": f"a{i}"})
        messages.append({"role": "user", "content": f"obs{i}"})

    pruned = agent._prune(messages)

    assert pruned[0]["content"] == "sys"
    assert pruned[1]["content"] == "goal"
    assert "4 earlier step(s) elided" in pruned[2]["content"]
    assert pruned[-1]["content"] == "obs5"


def test_pruning_reports_cumulative_elisions() -> None:
    agent = ReActAgent(_registry(), log=False, history_pairs=3)
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "goal"}]
    for i in range(10):
        messages.append({"role": "assistant", "content": f"a{i}"})
        messages.append({"role": "user", "content": f"obs{i}"})

    first = agent._prune(messages)
    first.extend([
        {"role": "assistant", "content": "a10"},
        {"role": "user", "content": "obs10"},
    ])
    second = agent._prune(first)

    assert "8 earlier step(s) elided" in second[2]["content"]
