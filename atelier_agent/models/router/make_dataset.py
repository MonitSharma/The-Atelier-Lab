"""Generate a synthetic difficulty-classification dataset for the router.

Phase 6's thesis: send *easy* subtasks to a cheap small model and reserve the
brain (14B) for *hard* ones. To route, we need a fast classifier. We fine-tune a
tiny local model (Qwen2.5-0.5B) to label a task "easy" or "hard".

This script writes train/valid/test JSONL in mlx-lm's prompt/completion format.
The data is templated (and thus in-distribution for the test split) — we report
that honestly in the writeup; the point is to demonstrate the fine-tune lifts a
0.5B model from near-chance to a usable router, and that routing saves brain
calls without hurting success.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

random.seed(7)

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

PROMPT = (
    "Classify the difficulty of this task for an AI agent as exactly 'easy' or "
    "'hard'. Easy = a small model can do it in one shot (arithmetic, a single "
    "fact, a one-line edit, a format change). Hard = needs multi-step reasoning, "
    "design, or changes across multiple files.\n\nTask: {task}\nDifficulty:"
)

# --- Easy task templates -----------------------------------------------------
EASY = [
    lambda: f"What is {random.randint(11,99)} * {random.randint(11,99)}?",
    lambda: f"Compute {random.randint(100,999)} + {random.randint(100,999)}.",
    lambda: f"Convert the string '{random.choice(['hello','atelier','router'])}' to uppercase.",
    lambda: f"What is the capital of {random.choice(['France','Japan','Egypt','Peru'])}?",
    lambda: "Fix this one-line bug: `return a - b` should add a and b.",
    lambda: f"Rename the variable `{random.choice(['x','tmp','val'])}` to `count` in one line.",
    lambda: f"Round {random.uniform(1,9):.3f} to two decimal places.",
    lambda: "Add a docstring to a single function.",
    lambda: f"Reverse the list [{random.randint(1,9)}, {random.randint(1,9)}, {random.randint(1,9)}].",
    lambda: "Change the default timeout value from 30 to 60 in one config line.",
    lambda: f"Is {random.randint(2,99)} an even number?",
    lambda: "Format this dict as pretty-printed JSON.",
]

# --- Hard task templates -----------------------------------------------------
HARD = [
    lambda: "Refactor the authentication module to support OAuth across the codebase.",
    lambda: "Find and fix a race condition that only appears under concurrent load.",
    lambda: "Design a caching layer and integrate it into the request pipeline.",
    lambda: "Migrate the data store from JSON files to SQLite, updating all callers.",
    lambda: "Diagnose why tests pass locally but fail in CI, then fix the root cause.",
    lambda: "Implement a new feature spanning the API, the service layer, and the database.",
    lambda: "Reduce end-to-end latency by profiling and optimizing the hot path.",
    lambda: "Write a multi-step proof that the scheduling algorithm is correct.",
    lambda: "Trace a memory leak across several modules and eliminate it.",
    lambda: "Redesign the plugin system so third-party tools can register safely.",
    lambda: "Plan and execute a backward-compatible breaking change to the public API.",
    lambda: "Synthesize a strategy from three conflicting design documents.",
]


def _rows(templates: list, label: str, n: int) -> list[dict]:
    out = []
    for _ in range(n):
        task = random.choice(templates)()
        out.append({"prompt": PROMPT.format(task=task), "completion": f" {label}"})
    return out


def build(n_per_class: int = 160) -> None:
    rows = _rows(EASY, "easy", n_per_class) + _rows(HARD, "hard", n_per_class)
    random.shuffle(rows)
    n = len(rows)
    train, valid, test = rows[: int(n * 0.8)], rows[int(n * 0.8): int(n * 0.9)], rows[int(n * 0.9):]

    DATA.mkdir(parents=True, exist_ok=True)
    for name, split in (("train", train), ("valid", valid), ("test", test)):
        (DATA / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(r) for r in split) + "\n"
        )
    print(f"wrote {len(train)} train / {len(valid)} valid / {len(test)} test to {DATA}")


if __name__ == "__main__":
    build()
