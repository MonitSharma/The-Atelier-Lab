from pathlib import Path
from typing import Any

from tools.base import Tool

PROJECT_ROOT = Path.cwd().resolve()

def _resolve_workspace_path(path: str) -> Path:
    """
    Resolve a user supplied path and esure it stas inside the project
    """

    requested_path = Path(path)

    if requested_path.is_absolute():
        resolved_path = requested_path.resolve()
    else:
        resolved_path = (PROJECT_ROOT / requested_path).resolve()

    try: 
        resolved_path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(
                f"Path is outside the project workspace: {path}"
                ) from exc
    
    return resolved_path


def run_read_file(arguments: dict[str, Any]) -> dict[str,Any]:
    """
    Read a UTF-8 text file inside the project workspace
    """
    path = arguments.get("path")

    if not isinstance(path,str):
        return {
                "status": "error",
                "error_type": "invalid_arguments",
                "message": "read_file requires a string argument named 'path'.",
                }

    try:
        resolved_path = _resolve_workspace_path(path)
    except ValueError as exc:
        return {
                "status": "error",
                "error_type": "path_not_allowed",
                "message": str(exc),
                }

    if not resolved_path.exists():
        return {
                "status": "error",
                "error_type": "file_not_found",
                "message": f"No file exists at path: {path}",
                }

    if not resolved_path.is_file():
        return {
                "status": "error",
                "error_type": "not_a_file",
                "message": f"Path is not a file: {path}",
                }

    try:
        content = resolved_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
                "status": "error",
                "error_type": "decode_error",
                "message": f"File is not valid UTF-8 text: {path}",
                }
    except OSError as exc:
        return {
                "status": "error",
                "error_type": "read_error",
                "message": str(exc),
                }

    return {
                "status": "success",
                "tool": "read_file",
                "path": path,
                "resolved_path": str(resolved_path),
                "content": content,
                }



READ_FILE_TOOL = Tool(
    name="read_file",
    description=(
        "Read a UTF-8 text file inside the project workspace. "
        "Use this when you need to inspect project files such as README.md, "
        "PROJECT.md, Python source files, or test files."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": (
                    "Path to a text file inside the project workspace, "
                    "for example 'PROJECT.md' or 'agent/loop.py'."
                ),
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
    function=run_read_file,
)


def run_write_file(arguments: dict[str, Any]) -> dict[str, Any]:
    """Create or overwrite a UTF-8 text file inside the project workspace."""
    path = arguments.get("path")
    content = arguments.get("content")

    if not isinstance(path, str):
        return {
            "status": "error",
            "error_type": "invalid_arguments",
            "message": "write_file requires a string argument named 'path'.",
        }
    if not isinstance(content, str):
        return {
            "status": "error",
            "error_type": "invalid_arguments",
            "message": "write_file requires a string argument named 'content'.",
        }

    try:
        resolved_path = _resolve_workspace_path(path)
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}

    try:
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error_type": "write_error", "message": str(exc)}

    return {
        "status": "success",
        "tool": "write_file",
        "path": path,
        "bytes_written": len(content.encode("utf-8")),
    }


def run_edit_file(arguments: dict[str, Any]) -> dict[str, Any]:
    """Replace an exact, unique substring in a workspace file.

    Mirrors how careful code edits work: ``old_string`` must occur exactly once,
    so the model can't silently change the wrong location.
    """
    path = arguments.get("path")
    old_string = arguments.get("old_string")
    new_string = arguments.get("new_string")

    for name, val in (("path", path), ("old_string", old_string), ("new_string", new_string)):
        if not isinstance(val, str):
            return {
                "status": "error",
                "error_type": "invalid_arguments",
                "message": f"edit_file requires a string argument named '{name}'.",
            }

    try:
        resolved_path = _resolve_workspace_path(path)
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}

    if not resolved_path.is_file():
        return {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"No file exists at path: {path}",
        }

    text = resolved_path.read_text(encoding="utf-8")
    occurrences = text.count(old_string)
    if occurrences == 0:
        return {
            "status": "error",
            "error_type": "string_not_found",
            "message": "old_string was not found in the file.",
        }
    if occurrences > 1:
        return {
            "status": "error",
            "error_type": "string_not_unique",
            "message": f"old_string occurs {occurrences} times; make it unique.",
        }

    resolved_path.write_text(text.replace(old_string, new_string), encoding="utf-8")
    return {"status": "success", "tool": "edit_file", "path": path, "replacements": 1}


WRITE_FILE_TOOL = Tool(
    name="write_file",
    description=(
        "Create or overwrite a text file inside the project workspace. "
        "Creates parent directories as needed. Use for new files or full rewrites."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path."},
            "content": {"type": "string", "description": "Full file contents to write."},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
    function=run_write_file,
)


EDIT_FILE_TOOL = Tool(
    name="edit_file",
    description=(
        "Replace an exact, unique substring in an existing workspace file. "
        "old_string must appear exactly once. Prefer this over write_file for "
        "small, targeted changes."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path."},
            "old_string": {"type": "string", "description": "Exact text to replace (must be unique)."},
            "new_string": {"type": "string", "description": "Replacement text."},
        },
        "required": ["path", "old_string", "new_string"],
        "additionalProperties": False,
    },
    function=run_edit_file,
)





