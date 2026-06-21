"""shell tool — run a shell command in the workspace, with a timeout.

This is the most powerful (and bluntest) tool. It is NOT sandboxed beyond a
timeout and a working-directory pin; it can do anything your user account can.
A small denylist blocks the most obvious foot-guns, but treat enabling this tool
as trusting the model with your shell. It is opt-in: not part of the default
registry. Construct a registry with ``include_shell=True`` to use it.
"""

from __future__ import annotations

import subprocess
from typing import Any

from tools.base import Tool
from tools.files import _resolve_workspace_path

DEFAULT_TIMEOUT = 60

# Obvious destructive / exfiltration patterns we refuse outright.
_DENY = ("rm -rf /", "rm -rf ~", ":(){", "mkfs", "dd if=", "> /dev/sd",
         "shutdown", "reboot", "curl ", "wget ", "scp ", "nc ")


def run_shell(arguments: dict[str, Any]) -> dict[str, Any]:
    command = arguments.get("command")
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)
    if not isinstance(command, str) or not command.strip():
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "shell requires a non-empty string 'command'."}
    lowered = command.lower()
    if any(bad in lowered for bad in _DENY):
        return {"status": "error", "error_type": "blocked",
                "message": "Command blocked by safety denylist."}
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
        timeout = DEFAULT_TIMEOUT

    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(_resolve_workspace_path(".")),
        )
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_type": "timeout",
                "message": f"Command exceeded {timeout}s."}

    return {
        "status": "success" if proc.returncode == 0 else "error",
        "error_type": None if proc.returncode == 0 else "nonzero_exit",
        "tool": "shell",
        "returncode": proc.returncode,
        "stdout": proc.stdout[-6000:],
        "stderr": proc.stderr[-6000:],
    }


SHELL_TOOL = Tool(
    name="shell",
    description=(
        "Run a shell command in the project workspace and return "
        "stdout/stderr/returncode. Powerful and only lightly guarded — use for "
        "build/test/inspection commands, not destructive operations."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run."},
            "timeout": {"type": "number", "description": "Seconds before kill (default 60, max 300)."},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
    function=run_shell,
)
