"""Run a test suite and report structured pass/fail — build mode's verifier.

This is the objective signal (PROJECT.md §2): a code change is only "done" when
the tests it must satisfy go green. We shell out to pytest inside the workspace
and parse the summary line so the agent gets clean numbers, not raw log soup.
"""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

from tools.base import Tool
from tools.files import _resolve_workspace_path

DEFAULT_TIMEOUT = 300

# e.g. "5 passed, 1 failed, 2 warnings in 0.41s"
_SUMMARY_RE = re.compile(
    r"(?:(\d+) passed)?(?:.*?(\d+) failed)?(?:.*?(\d+) error)?(?:.*?(\d+) skipped)?",
)


def _parse_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for kind in counts:
        m = re.search(rf"(\d+) {kind}", output)
        if m:
            counts[kind] = int(m.group(1))
    return counts


def run_tests(arguments: dict[str, Any]) -> dict[str, Any]:
    target = arguments.get("path", ".")
    expr = arguments.get("k")  # optional -k filter
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)

    if not isinstance(target, str):
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "test_runner 'path' must be a string."}
    try:
        resolved = _resolve_workspace_path(target)
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}

    cmd = [sys.executable, "-m", "pytest", str(resolved), "-q", "--no-header"]
    if isinstance(expr, str) and expr:
        cmd += ["-k", expr]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            cwd=str(_resolve_workspace_path(".")),
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_type": "timeout",
                "message": f"Tests exceeded {timeout}s."}

    output = proc.stdout + "\n" + proc.stderr
    counts = _parse_counts(output)
    passed_clean = proc.returncode == 0

    return {
        "status": "success",
        "tool": "test_runner",
        "passed_clean": passed_clean,   # True only if pytest exited 0
        "returncode": proc.returncode,
        "counts": counts,
        "summary": output.strip().splitlines()[-1] if output.strip() else "",
        "output_tail": output[-6000:],
    }


TEST_RUNNER_TOOL = Tool(
    name="test_runner",
    description=(
        "Run the pytest suite for a path inside the workspace and return "
        "structured results (passed/failed/error counts, whether it passed "
        "cleanly, and the output tail). This is how you PROVE a code change works."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace path to test (default '.')."},
            "k": {"type": "string", "description": "Optional pytest -k filter expression."},
            "timeout": {"type": "number", "description": "Seconds before kill (default 300)."},
        },
        "required": [],
        "additionalProperties": False,
    },
    function=run_tests,
)
