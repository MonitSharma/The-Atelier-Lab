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
        "[dim]Commands: search · ask · paper · ingest · sources · "
        "doctor · agent · workspace · serve · mcp · remember · recall · help · exit[/]\n"
    )

    executable = shutil.which("atelier")
    command = [executable] if executable else [sys.executable, "-m", "atelier.cli"]

    env = os.environ.copy()
    env["ATELIER_NO_BANNER"] = "1"

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

        try:
            subprocess.run([*command, *args], env=env, check=False)
        except KeyboardInterrupt:
            console.print("[yellow]command cancelled; Atelier session remains open[/]")
        console.print()
