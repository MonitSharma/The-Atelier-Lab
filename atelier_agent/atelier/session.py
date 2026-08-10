"""Interactive Atelier workbench session."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

try:
    import readline
except ImportError:  # pragma: no cover - readline is available on supported Macs.
    readline = None  # type: ignore[assignment]

from rich.console import Console

from atelier.banner import print_banner

_ATELIER_COMMANDS = (
    "guide",
    "advanced-help",
    "search",
    "ask",
    "paper",
    "ingest",
    "sources",
    "doctor",
    "agent",
    "workspace",
    "remember",
    "recall",
    "repo",
    "code-fix",
    "models",
)
_TERMINAL_COMMANDS = (
    "cd",
    "pwd",
    "ls",
    "find",
    "rg",
    "git",
    "cat",
    "ollama",
    "clear",
    "help",
    "exit",
    "quit",
)
_PATH_COMMANDS = {
    "cd",
    "cat",
    "find",
    "rg",
    "paper",
    "paper-visual",
    "ingest",
    "repo",
    "code-fix",
}


def _command_tokens_before_cursor(line: str, begin: int) -> list[str]:
    """Return simple command tokens before the readline cursor."""
    tokens = line[:begin].strip().split()
    if tokens and Path(tokens[0]).name == "atelier":
        tokens = tokens[1:]
    return tokens


def _path_completion_request(line: str, begin: int) -> tuple[bool, bool]:
    """Return ``(is_path, directories_only)`` for the current command."""
    tokens = _command_tokens_before_cursor(line, begin)
    if not tokens:
        return False, False
    command = tokens[0]
    if command == "cd":
        return True, True
    if command == "workspace" and len(tokens) >= 2 and tokens[1] == "add":
        return True, True
    if command == "repo" and len(tokens) >= 2 and tokens[1] in {
        "inspect", "status", "symbols", "tests"
    }:
        return True, True
    if command in _PATH_COMMANDS:
        return True, False
    return False, False


def _path_completion_input(line: str, begin: int, text: str) -> tuple[str, str]:
    """Reconstruct a slash-delimited path and its readline replacement prefix."""
    before = line[:begin]
    if before and not before[-1].isspace():
        path_prefix = before.rsplit(None, 1)[-1]
    else:
        path_prefix = ""
    return path_prefix + text, path_prefix


def _path_completions(
    text: str,
    *,
    directories_only: bool = False,
    cwd: str | os.PathLike[str] | None = None,
) -> list[str]:
    """Return readable readline candidates for a partially typed path."""
    current = Path(cwd or os.getcwd()).resolve()
    expanded = os.path.expanduser(text)
    absolute = os.path.isabs(expanded)

    if expanded.endswith(os.sep):
        directory = Path(expanded)
        prefix = ""
    else:
        typed = Path(expanded)
        directory = typed.parent
        prefix = typed.name

    if not directory.is_absolute():
        directory = current / directory

    try:
        entries = sorted(directory.iterdir(), key=lambda entry: entry.name.lower())
    except (OSError, ValueError):
        return []

    candidates: list[str] = []
    for entry in entries:
        if not entry.name.startswith(prefix):
            continue
        if entry.name.startswith(".") and not prefix.startswith("."):
            continue
        try:
            is_directory = entry.is_dir()
        except OSError:
            continue
        if directories_only and not is_directory:
            continue

        if text.startswith("~"):
            home = Path(os.path.expanduser("~")).resolve()
            try:
                candidate = "~" + os.sep + str(entry.relative_to(home))
            except ValueError:
                candidate = str(entry)
        elif absolute:
            candidate = str(entry)
        else:
            candidate = os.path.relpath(entry, current)
            if text.startswith("./") and not candidate.startswith("."):
                candidate = "." + os.sep + candidate

        if is_directory:
            candidate += os.sep
        candidates.append(candidate)
    return candidates


def _command_completions(text: str) -> list[str]:
    """Return Atelier and ordinary terminal commands matching ``text``."""
    commands = sorted(set(_ATELIER_COMMANDS + _TERMINAL_COMMANDS))
    return [command for command in commands if command.startswith(text)]


class _AtelierCompleter:
    """Readline completer for Atelier commands and local filesystem paths."""

    def complete(self, text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        begin = readline.get_begidx()
        tokens = _command_tokens_before_cursor(line, begin)

        if begin == 0:
            candidates = _command_completions(text)
        else:
            is_path, directories_only = _path_completion_request(line, begin)
            if is_path:
                lookup_text, replacement_prefix = _path_completion_input(line, begin, text)
                candidates = _path_completions(lookup_text, directories_only=directories_only)
                if replacement_prefix:
                    candidates = [
                        candidate[len(replacement_prefix):]
                        if candidate.startswith(replacement_prefix)
                        else candidate
                        for candidate in candidates
                    ]
            elif tokens and len(tokens) == 1 and tokens[0] == "atelier":
                candidates = _command_completions(text)
            else:
                candidates = []

        return candidates[state] if state < len(candidates) else None


def _install_readline(completer: _AtelierCompleter) -> tuple[ModuleType, Any, str] | None:
    """Install completion only for a real terminal; return state for cleanup."""
    if readline is None or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return None
    try:
        readline_module = readline
        previous_completer = readline_module.get_completer()
        previous_delims = readline_module.get_completer_delims()
        readline_module.set_completer(completer.complete)
        # GNU readline uses the first binding; macOS's libedit accepts the
        # second form. Applying both keeps completion working on either build.
        for binding in ("tab: complete", "bind ^I rl_complete"):
            try:
                readline_module.parse_and_bind(binding)
            except (ValueError, RuntimeError):
                pass
        return readline_module, previous_completer, previous_delims
    except (AttributeError, ImportError):
        return None


def _restore_readline(state: tuple[ModuleType, Any, str] | None) -> None:
    if state is None:
        return
    readline_module, previous_completer, previous_delims = state
    readline_module.set_completer(previous_completer)
    readline_module.set_completer_delims(previous_delims)


def _readline_input(console: Console, prompt: str, enabled: bool) -> str:
    """Read a line with completion when available, Rich input otherwise."""
    if enabled:
        return input(prompt)
    return console.input(prompt)


def run_session(console: Console | None = None) -> None:
    """Run a thin interactive shell over the canonical Atelier CLI."""
    console = console or Console()
    print_banner(console)
    console.print(
        "[dim]Core: ingest · ask · search · sources · agent · code-fix · doctor[/]\n"
        "[dim]Also: paper · remember · recall · workspace · repo · models[/]\n"
        "[dim]Advanced commands remain available: type advanced-help[/]\n"
        "[dim]Terminal: cd · pwd · ls · find · rg · git · cat · ollama · help · exit[/]\n"
        "[dim]Tab completes Atelier commands and local paths.[/]\n"
    )

    executable = shutil.which("atelier")
    command = [executable] if executable else [sys.executable, "-m", "atelier.cli"]

    env = os.environ.copy()
    env["ATELIER_NO_BANNER"] = "1"
    previous_cwd = os.getcwd()

    completer = _AtelierCompleter()
    readline_state = _install_readline(completer)
    try:
        while True:
            try:
                line = _readline_input(
                    console, "\033[1;36matelier ›\033[0m ", readline_state is not None
                ).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]session closed[/]")
                return

            if not line:
                continue

            # Support the familiar shell continuation form. The interactive
            # prompt is line-oriented, so collect continuation lines before
            # handing the complete command to shlex.
            while line.endswith("\\"):
                line = line[:-1].rstrip()
                try:
                    continuation = _readline_input(
                        console, "\033[2m... \033[0m", readline_state is not None
                    ).strip()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[yellow]continued command cancelled[/]")
                    line = ""
                    break
                line = f"{line} {continuation}"
            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                console.print("[dim]session closed[/]")
                return
            if line.lower() in {"clear", "cls"}:
                console.clear()
                print_banner(console)
                continue
            if line.lower() == "help":
                subprocess.run([*command, "guide"], env=env, check=False)
                continue

            try:
                args = shlex.split(line)
            except ValueError as exc:
                console.print(f"[red]Parse error:[/] {exc}")
                continue

            # Inside Atelier, `atelier workspace ...` is a convenient harmless
            # prefix even though the session normally accepts `workspace ...`.
            if args and Path(args[0]).name == "atelier":
                args = args[1:]
            if not args:
                continue

            # A normal shell expands a leading `~`; this session invokes
            # subprocesses without a shell, so expand it explicitly.
            args = [os.path.expanduser(arg) if arg.startswith("~") else arg for arg in args]

            if args[0] == "cd":
                if len(args) > 2:
                    console.print("[red]Usage:[/] cd [DIRECTORY]")
                    continue
                target = os.path.expanduser(args[1]) if len(args) == 2 else os.path.expanduser("~")
                if target == "-":
                    target = previous_cwd
                candidate = os.path.abspath(target)
                if not os.path.isdir(candidate):
                    console.print(f"[red]cd:[/] no such directory: {target}")
                    continue
                previous_cwd, _ = os.getcwd(), candidate
                os.chdir(candidate)
                console.print(f"[dim]{os.getcwd()}[/]")
                continue

            if args[0] == "pwd":
                console.print(os.getcwd())
                continue

            # Run ordinary terminal programs in the session's current directory.
            # Shell syntax such as pipes/redirection is intentionally not evaluated;
            # use a normal terminal for that, while commands like `ls -la` and
            # `git status` work directly here.
            if shutil.which(args[0]):
                try:
                    subprocess.run(args, env=env, check=False)
                except KeyboardInterrupt:
                    console.print("[yellow]command cancelled; Atelier session remains open[/]")
                console.print()
                continue

            try:
                subprocess.run([*command, *args], env=env, check=False)
            except KeyboardInterrupt:
                console.print("[yellow]command cancelled; Atelier session remains open[/]")
            console.print()
    finally:
        _restore_readline(readline_state)
