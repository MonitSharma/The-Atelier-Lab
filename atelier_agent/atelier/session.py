"""Interactive Atelier workbench session."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys

from rich.console import Console

from atelier.banner import print_banner


def run_session(console: Console | None = None) -> None:
    """Run a thin interactive shell over the canonical Atelier CLI."""
    console = console or Console()
    print_banner(console)
    console.print(
        "[dim]Atelier: search · ask · paper · ingest · sources · doctor · agent · "
        "workspace · serve · mcp · remember · recall[/]\n"
        "[dim]Terminal: cd · pwd · ls · find · rg · git · cat · ollama · help · exit[/]\n"
    )

    executable = shutil.which("atelier")
    command = [executable] if executable else [sys.executable, "-m", "atelier.cli"]

    env = os.environ.copy()
    env["ATELIER_NO_BANNER"] = "1"
    previous_cwd = os.getcwd()

    while True:
        try:
            line = console.input("[bold cyan]atelier ›[/] ").strip()
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
            subprocess.run([*command, "--help"], env=env, check=False)
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
