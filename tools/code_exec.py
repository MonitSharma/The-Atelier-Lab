"""Sandboxed Python execution tool.

What this gives you (honestly):
  * a fresh subprocess with a hard **timeout** (no runaway loops);
  * a **temp working directory**, so generated files don't litter the repo;
  * best-effort **network isolation** via macOS ``sandbox-exec`` (seatbelt) —
    when available, the child process cannot open sockets, which upholds the
    project's "nothing leaves the machine" promise even for model-written code.

What it is NOT: a hardened security boundary against a determined adversary.
``sandbox-exec`` is deprecated (though still functional on current macOS) and we
fall back to a plain subprocess if it's missing. Treat this as "safe enough to
run a coding agent's own scratch code on your machine," not "run untrusted
malware." The ``network_blocked`` flag in the result tells you which mode ran.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.base import Tool

DEFAULT_TIMEOUT = 15

# Seatbelt profile: allow everything except network. Keeps the agent's code from
# phoning home while letting it read/write its temp dir, import stdlib, etc.
_SEATBELT_PROFILE = "(version 1)(allow default)(deny network*)"
_SANDBOX_EXEC = shutil.which("sandbox-exec")


def run_python(arguments: dict[str, Any]) -> dict[str, Any]:
    code = arguments.get("code")
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)

    if not isinstance(code, str):
        return {
            "status": "error",
            "error_type": "invalid_arguments",
            "message": "code_exec requires a string argument named 'code'.",
        }
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 120:
        timeout = DEFAULT_TIMEOUT

    with tempfile.TemporaryDirectory(prefix="atelier_exec_") as tmp:
        script = Path(tmp) / "snippet.py"
        script.write_text(code, encoding="utf-8")

        base_cmd = [sys.executable, "-I", str(script)]  # -I = isolated mode
        if _SANDBOX_EXEC:
            cmd = [_SANDBOX_EXEC, "-p", _SEATBELT_PROFILE, *base_cmd]
            network_blocked = True
        else:
            cmd = base_cmd
            network_blocked = False

        try:
            proc = subprocess.run(
                cmd,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error_type": "timeout",
                "message": f"Execution exceeded {timeout}s and was killed.",
                "network_blocked": network_blocked,
            }

        return {
            "status": "success" if proc.returncode == 0 else "error",
            "error_type": None if proc.returncode == 0 else "nonzero_exit",
            "tool": "code_exec",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
            "network_blocked": network_blocked,
        }


CODE_EXEC_TOOL = Tool(
    name="code_exec",
    description=(
        "Execute a snippet of Python in a sandboxed subprocess (timeout + temp "
        "dir + best-effort network block) and return stdout/stderr/returncode. "
        "Use this to compute, verify logic, or test small pieces of code. The "
        "snippet must print results you want to see."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to run."},
            "timeout": {"type": "number", "description": "Seconds before kill (default 15, max 120)."},
        },
        "required": ["code"],
        "additionalProperties": False,
    },
    function=run_python,
)
