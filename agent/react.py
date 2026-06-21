"""The general ReAct agent: reason → act (tool) → observe → repeat → answer.

Generalizes the Phase-0 calculator loop into a registry-driven engine that
drives the whole toolbox (knowledge + build). Design choices that matter:

* **JSON mode** for every model turn, so tool calls parse reliably.
* **Reflection**: a tool error (or malformed output) is fed back as an
  observation rather than crashing, so the model can recover — the mechanism
  that lets build mode read a test failure and try again (PROJECT.md §8 Phase 4).
* **Observation capping**: large tool outputs (a file dump, a test log) are
  truncated before re-entering context, so a single step can't blow the window.
* **Trace logging**: every run is written to ``data/traces`` for debugging and
  the eventual eval harness (PROJECT.md §9).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from agent.brain import chat
from atelier.config import settings
from tools.registry import ToolRegistry, create_default_registry

MAX_OBSERVATION_CHARS = 8000

SYSTEM_TEMPLATE = """\
You are Atelier, a local AI agent that completes tasks by reasoning and using \
tools. You work in a loop: think, optionally call ONE tool, observe its result, \
then either call another tool or give a final answer.

Available tools:

{tools}

Respond with EXACTLY ONE JSON object and nothing else. Two shapes are allowed:

Tool call:
{{"type": "tool_call", "thought": "<one short sentence: why this tool>", "tool": "<tool name>", "arguments": {{ ... }}}}

Final answer:
{{"type": "final", "answer": "<your complete answer>"}}

Rules:
- Use `search_notes` for anything about the user's own notes, decisions, or documents.
- For coding tasks: call `repo_map` first to understand the layout, `read_file` to \
inspect, `write_file`/`edit_file` to change code, and `test_runner` to PROVE it works.
- NEVER claim a code change works unless `test_runner` returned passed_clean = true.
- If a tool returns an error, read the message and adjust. Do not repeat an identical failing call.
- Keep `arguments` valid against each tool's input schema. Emit only the JSON object.
"""


class AgentError(RuntimeError):
    """Raised when the agent cannot complete the task within its budget."""


@dataclass
class AgentResult:
    answer: str | None
    success: bool
    steps: int
    trace: list[dict[str, Any]] = field(default_factory=list)
    trace_path: str | None = None


def _clean_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    decision = json.loads(text)  # raises JSONDecodeError on bad output
    if not isinstance(decision, dict):
        raise ValueError("model response was not a JSON object")
    if decision.get("type") not in {"tool_call", "final"}:
        raise ValueError("type must be 'tool_call' or 'final'")
    return decision


def _truncate(obj: dict[str, Any]) -> str:
    s = json.dumps(obj, default=str)
    if len(s) > MAX_OBSERVATION_CHARS:
        return s[:MAX_OBSERVATION_CHARS] + " …[truncated]"
    return s


class ReActAgent:
    def __init__(
        self,
        registry: ToolRegistry | None = None,
        *,
        role: str = "brain",
        max_steps: int = 10,
        verbose: bool = False,
        log: bool = True,
        on_event: Any = None,
    ) -> None:
        self.registry = registry or create_default_registry()
        self.role = role
        self.max_steps = max_steps
        self.verbose = verbose
        self.log = log
        self.on_event = on_event  # optional callable(event: dict) for UIs

    def _emit(self, event: dict[str, Any]) -> None:
        if self.verbose:
            print(json.dumps(event)[:500])
        if self.on_event:
            self.on_event(event)

    def _save_trace(self, goal: str, trace: list[dict[str, Any]]) -> str | None:
        if not self.log:
            return None
        settings.ensure_dirs()
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = settings.traces_dir / f"{ts}.json"
        path.write_text(json.dumps({"goal": goal, "trace": trace}, indent=2, default=str))
        return str(path)

    def run(self, goal: str) -> AgentResult:
        system = SYSTEM_TEMPLATE.format(tools=self.registry.prompt_description())
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": goal},
        ]
        trace: list[dict[str, Any]] = []

        for step in range(1, self.max_steps + 1):
            t0 = time.time()
            raw = chat(messages, role=self.role, json_mode=True)
            entry: dict[str, Any] = {"step": step, "raw": raw, "latency_s": round(time.time() - t0, 2)}

            try:
                decision = _clean_json(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                err = {"status": "error", "error_type": "invalid_model_output", "message": str(exc)}
                entry["error"] = err
                trace.append(entry)
                self._emit({"step": step, "kind": "parse_error", "detail": str(exc)})
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content":
                                 "Your last response was not valid. Return exactly one JSON "
                                 f"object using the required schema. Error: {json.dumps(err)}"})
                continue

            entry["decision"] = decision

            if decision["type"] == "final":
                answer = decision.get("answer", "")
                entry["final"] = answer
                trace.append(entry)
                self._emit({"step": step, "kind": "final", "answer": answer})
                return AgentResult(answer=answer, success=True, steps=step,
                                   trace=trace, trace_path=self._save_trace(goal, trace))

            tool_name = decision.get("tool")
            arguments = decision.get("arguments", {})
            self._emit({"step": step, "kind": "tool_call", "tool": tool_name,
                        "thought": decision.get("thought", ""), "arguments": arguments})

            if not isinstance(tool_name, str):
                observation = {"status": "error", "error_type": "invalid_tool_name",
                               "message": "tool must be a string."}
            elif not isinstance(arguments, dict):
                observation = {"status": "error", "error_type": "invalid_arguments",
                               "message": "arguments must be a JSON object."}
            else:
                observation = self.registry.execute(tool_name, arguments)

            entry["tool"] = tool_name
            entry["observation"] = observation
            trace.append(entry)
            self._emit({"step": step, "kind": "observation",
                        "status": observation.get("status"), "tool": tool_name})

            messages.append({"role": "assistant", "content": raw})
            messages.append({"role": "user", "content":
                             f"TOOL OBSERVATION:\n{_truncate(observation)}\n\n"
                             "Use this to decide your next action."})

        trace_path = self._save_trace(goal, trace)
        return AgentResult(answer=None, success=False, steps=self.max_steps,
                           trace=trace, trace_path=trace_path)


def run_task(goal: str, *, role: str = "brain", max_steps: int = 10,
             include_shell: bool = False, verbose: bool = False) -> AgentResult:
    """Convenience entry point: full toolbox, one call."""
    agent = ReActAgent(create_default_registry(include_shell=include_shell),
                       role=role, max_steps=max_steps, verbose=verbose)
    return agent.run(goal)
