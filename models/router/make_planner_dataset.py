"""Build Atelier-specific planner/router SFT data from frozen eval metadata.

This is different from the early synthetic easy/hard router dataset. These rows
teach a small model Atelier's own task taxonomy:

    task -> category, difficulty, edit_scope, tool_plan, model_route

The output uses the same mlx-lm prompt/completion JSONL shape as the existing
router data.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "models" / "router" / "data"

PROMPT = """\
You are Atelier's planner-router. Given a user task, return a compact JSON plan.
Fields:
- category: task family
- difficulty: easy or medium or hard
- edit_scope: none, single_line, multi_line, or multi_file
- tool_plan: ordered tool names Atelier should use
- model_route: worker, brain, or heavy

Task: {task}
Plan:
"""


def _route(difficulty: str, edit_scope: str, combined: bool = False) -> str:
    if combined:
        return "brain"
    if difficulty == "easy" and edit_scope in {"none", "single_line"}:
        return "worker"
    if difficulty == "hard":
        return "heavy"
    return "brain"


def _completion(category: str, difficulty: str, edit_scope: str, tool_plan: list[str],
                model_route: str) -> str:
    return " " + json.dumps({
        "category": category,
        "difficulty": difficulty,
        "edit_scope": edit_scope,
        "tool_plan": tool_plan,
        "model_route": model_route,
    }, separators=(",", ":"))


def _docqa_rows() -> list[dict[str, str]]:
    spec = json.loads((ROOT / "eval" / "tasks_docqa" / "tasks.json").read_text())
    rows = []
    for task in spec["tasks"]:
        difficulty = task.get("difficulty", "easy")
        category = task.get("category", "docqa")
        rows.append({
            "prompt": PROMPT.format(task=task["question"]),
            "completion": _completion(
                category=category,
                difficulty=difficulty,
                edit_scope="none",
                tool_plan=["search_notes"],
                model_route=_route(difficulty, "none"),
            ),
        })
    return rows


def _task_dirs(path: Path) -> list[Path]:
    return sorted(d for d in path.iterdir() if d.is_dir() and (d / "task.json").exists())


def _code_rows() -> list[dict[str, str]]:
    rows = []
    for task_dir in _task_dirs(ROOT / "eval" / "tasks_code"):
        spec = json.loads((task_dir / "task.json").read_text())
        difficulty = spec.get("difficulty", "easy")
        edit_scope = spec.get("edit_scope", "single_line")
        edit_tool = "ast_edit" if edit_scope == "multi_line" else "edit_file"
        rows.append({
            "prompt": PROMPT.format(task=spec["prompt"].format(path=f"<{spec['id']}_workspace>")),
            "completion": _completion(
                category=spec.get("category", "code"),
                difficulty=difficulty,
                edit_scope=edit_scope,
                tool_plan=["repo_map", "read_file", edit_tool, "test_runner"],
                model_route=_route(difficulty, edit_scope),
            ),
        })
    return rows


def _combined_rows() -> list[dict[str, str]]:
    rows = []
    for task_dir in _task_dirs(ROOT / "eval" / "tasks_combined"):
        spec = json.loads((task_dir / "task.json").read_text())
        difficulty = spec.get("difficulty", "easy")
        edit_scope = spec.get("edit_scope", "single_line")
        edit_tool = "ast_edit" if edit_scope == "multi_line" else "edit_file"
        rows.append({
            "prompt": PROMPT.format(task=spec["prompt"].format(path=f"<{spec['id']}_workspace>")),
            "completion": _completion(
                category=spec.get("category", "combined"),
                difficulty=difficulty,
                edit_scope=edit_scope,
                tool_plan=["search_notes", "repo_map", "read_file", edit_tool, "test_runner"],
                model_route=_route(difficulty, edit_scope, combined=True),
            ),
        })
    return rows


def build(seed: int = 7) -> dict[str, Any]:
    rows = _docqa_rows() + _code_rows() + _combined_rows()
    random.Random(seed).shuffle(rows)

    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "planner_router.jsonl"
    out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    n = len(rows)
    train = rows[: max(1, int(n * 0.8))]
    valid = rows[len(train): max(len(train) + 1, int(n * 0.9))]
    test = rows[len(train) + len(valid):]
    for name, split in (
        ("planner_train", train),
        ("planner_valid", valid),
        ("planner_test", test),
    ):
        (DATA / f"{name}.jsonl").write_text("\n".join(json.dumps(r) for r in split) + "\n")

    summary = {
        "rows": n,
        "docqa": len(_docqa_rows()),
        "code": len(_code_rows()),
        "combined": len(_combined_rows()),
        "path": str(out),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()
