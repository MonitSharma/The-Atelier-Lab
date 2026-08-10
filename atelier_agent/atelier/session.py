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
        before = line[:begin]
        first_word = before.strip().split(maxsplit=1)[0] if before.strip() else ""

        if begin == 0:
            candidates = _command_completions(text)
        elif first_word == "cd":
            candidates = _path_completions(text, directories_only=True)
        elif first_word in _PATH_COMMANDS:
            candidates = _path_completions(text)
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
        return input("\033[1;36matelier ›\033[0m ")
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
                line = _readline_input(console, "[bold cyan]atelier ›[/] ", readline_state is not None).strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]session closed[/]")
                return

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
