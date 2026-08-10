"""shell tool — run one program in the workspace, with a timeout.

This is the most powerful (and bluntest) tool. It is NOT a sandbox: it has a
timeout, a working-directory pin, and an executable allowlist, but an allowed
program can still do anything your user account can — ``python -c ...`` most
obviously. Treat enabling this tool as trusting the model with your shell. It is
opt-in: not part of the default registry. Construct a registry with
``include_shell=True`` to use it.

The command is parsed once by :func:`atelier.security.parse_shell_command` and
the resulting argv is executed with ``shell=False``. There is deliberately no
shell process in the loop, so the allowlist cannot be bypassed by chaining a
second command with ``;``, ``&``, a newline, or any other separator.
"""

from __future__ import annotations

import subprocess
from typing import Any

from atelier.security import parse_shell_command
from atelier.workspace import WorkspaceError, current_workspace_context
from tools.base import Tool
from tools.files import _resolve_workspace_path

DEFAULT_TIMEOUT = 60

# Obvious destructive / exfiltration patterns we refuse outright.
_DENY = ("rm -rf /", "rm -rf ~", ":(){", "mkfs", "dd if=", "> /dev/sd",
         "shutdown", "reboot", "curl ", "wget ", "scp ", "nc ")
_NETWORK_MARKERS = (
    "git clone", "git fetch", "git pull", "git push", "pip install", "uv pip install",
    "npm install", "http://", "https://", "ssh ",
)


def run_shell(arguments: dict[str, Any]) -> dict[str, Any]:
    command = arguments.get("command")
    timeout = arguments.get("timeout", DEFAULT_TIMEOUT)
    if not isinstance(command, str) or not command.strip():
        return {"status": "error", "error_type": "invalid_arguments",
                "message": "shell requires a non-empty string 'command'."}
    argv, reason = parse_shell_command(
        command, allow_destructive=bool(arguments.get("_destructive_approved"))
    )
    if argv is None:
        return {"status": "denied", "error_type": "security_policy", "message": reason}
    lowered = command.lower()
    if any(bad in lowered for bad in _DENY):
        return {"status": "error", "error_type": "blocked",
                "message": "Command blocked by safety denylist."}
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
        timeout = DEFAULT_TIMEOUT

    try:
        context = current_workspace_context()
        if context is not None and any(marker in lowered for marker in _NETWORK_MARKERS):
            context.require_network()
        cwd = _resolve_workspace_path(".", "execute")
        proc = subprocess.run(
            argv, shell=False, capture_output=True, text=True,
            timeout=timeout, cwd=str(cwd),
        )
    except (ValueError, WorkspaceError) as exc:
        return {"status": "error", "error_type": "capability_denied", "message": str(exc)}
    except (FileNotFoundError, PermissionError) as exc:
        # shell=False surfaces a missing/unrunnable program directly rather than
        # as a 127 exit code from an intermediate shell.
        return {"status": "error", "error_type": "executable_not_found",
                "message": f"Could not run '{argv[0]}': {exc}"}
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
        "Run ONE program in the project workspace and return "
        "stdout/stderr/returncode. There is no shell: pipes, redirections, "
        "globs, and ';'/'&&' chaining are rejected — issue one command per call. "
        "Use for build/test/inspection commands, not destructive operations."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "One program and its arguments, e.g. 'pytest -q tests'. No pipes or redirection."},
            "timeout": {"type": "number", "description": "Seconds before kill (default 60, max 300)."},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
    function=run_shell,
)
