"""AST-aware Python editing tools.

The plain ``edit_file`` tool is intentionally strict: it replaces an exact
unique string. That is safe for small edits, but brittle for multi-line function
body rewrites because the model has to reproduce indentation perfectly. This
module adds a narrower structural edit: replace the body of a named Python
function and compile-check the result before writing it.
"""

from __future__ import annotations

import ast
import textwrap
from typing import Any

from tools.base import Tool
from tools.files import _py_syntax_report, _resolve_workspace_path


def _find_function(tree: ast.AST, function_name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find a top-level function or dotted class method such as ``Stats.median``."""
    parts = function_name.split(".")
    if len(parts) == 1:
        matches = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == parts[0]
        ]
    elif len(parts) == 2:
        class_name, method_name = parts
        matches = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                matches.extend(
                    child for child in node.body
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == method_name
                )
    else:
        return None

    if len(matches) != 1:
        return None
    return matches[0]


def _body_candidates(body: str) -> list[str]:
    """Return likely normalizations for a model-provided function body."""
    cleaned = textwrap.dedent(body).strip("\n")
    if not cleaned.strip():
        cleaned = "pass"
    candidates = [cleaned]

    lines = cleaned.splitlines()
    if lines and not lines[0].startswith((" ", "\t")):
        positive_indents = [
            len(line) - len(line.lstrip(" "))
            for line in lines[1:]
            if line.strip() and line.startswith(" ")
        ]
        if positive_indents:
            shift = min(positive_indents)
            shifted_lines = [lines[0]]
            for line in lines[1:]:
                if line.startswith(" " * shift):
                    shifted_lines.append(line[shift:])
                else:
                    shifted_lines.append(line)
            shifted = "\n".join(shifted_lines)
            if shifted not in candidates:
                candidates.append(shifted)

    return candidates


def _indent_body(body: str, indent: str) -> list[str]:
    """Indent a normalized function body while preserving relative indentation."""
    return [indent + line if line.strip() else "" for line in body.splitlines()]


def run_ast_edit(arguments: dict[str, Any]) -> dict[str, Any]:
    """Replace the body of a named Python function in a workspace file."""
    path = arguments.get("path")
    function_name = arguments.get("function_name")
    new_body = arguments.get("new_body")

    for name, value in (("path", path), ("function_name", function_name), ("new_body", new_body)):
        if not isinstance(value, str):
            return {
                "status": "error",
                "error_type": "invalid_arguments",
                "message": f"ast_edit requires a string argument named '{name}'.",
            }

    try:
        resolved_path = _resolve_workspace_path(path)
    except ValueError as exc:
        return {"status": "error", "error_type": "path_not_allowed", "message": str(exc)}

    if resolved_path.suffix != ".py":
        return {
            "status": "error",
            "error_type": "not_python",
            "message": "ast_edit only supports .py files.",
        }
    if not resolved_path.is_file():
        return {
            "status": "error",
            "error_type": "file_not_found",
            "message": f"No file exists at path: {path}",
        }

    text = resolved_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "status": "error",
            "error_type": "parse_error",
            "message": f"Existing file does not parse: {exc.msg} (line {exc.lineno})",
        }

    node = _find_function(tree, function_name)
    if node is None:
        return {
            "status": "error",
            "error_type": "function_not_found_or_ambiguous",
            "message": f"Expected exactly one function named '{function_name}'.",
        }
    if not node.body or node.end_lineno is None:
        return {
            "status": "error",
            "error_type": "unsupported_function_shape",
            "message": f"Could not determine the body range for '{function_name}'.",
        }

    lines = text.splitlines()
    body_start = node.body[0].lineno - 1
    body_end = node.end_lineno
    body_indent = " " * (node.col_offset + 4)
    syntax: dict[str, Any] = {"syntax_ok": False, "syntax_error": "Replacement did not compile."}
    new_text = ""
    replaced_body = ""
    for candidate in _body_candidates(new_body):
        replacement = _indent_body(candidate, body_indent)
        new_lines = lines[:body_start] + replacement + lines[body_end:]
        candidate_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")
        syntax = _py_syntax_report(resolved_path, candidate_text)
        if syntax.get("syntax_ok") is True:
            new_text = candidate_text
            replaced_body = candidate
            break
    else:
        return {
            "status": "error",
            "error_type": "syntax_error",
            "message": syntax.get("syntax_error", "Replacement did not compile."),
            **syntax,
        }

    try:
        resolved_path.write_text(new_text, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error_type": "write_error", "message": str(exc)}

    return {
        "status": "success",
        "tool": "ast_edit",
        "path": path,
        "function_name": function_name,
        "replaced_lines": body_end - body_start,
        "normalized_body": replaced_body != new_body.strip("\n"),
        **syntax,
    }


AST_EDIT_TOOL = Tool(
    name="ast_edit",
    description=(
        "Safely replace the body of a Python function by name. Use this for "
        "multi-line or structural Python edits where edit_file indentation is "
        "fragile. Provide only the new function body, not the def line. The "
        "tool compile-checks the result before writing."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative .py file path."},
            "function_name": {
                "type": "string",
                "description": "Function name, or dotted class method like 'ClassName.method'.",
            },
            "new_body": {
                "type": "string",
                "description": "Replacement function body without the def line.",
            },
        },
        "required": ["path", "function_name", "new_body"],
        "additionalProperties": False,
    },
    function=run_ast_edit,
)
