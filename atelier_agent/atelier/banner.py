"""Compact Atelier terminal identity."""

from __future__ import annotations

import os

from rich.console import Console

_HAT = r"""
          ✦
      ╭─────────╮
      │  ━━━━━  │
   ╭──┴─────────┴──╮
   ╰───────────────╯
"""

_WORDMARK = "       A T E L I E R"
_TAGLINE = "    local research workbench"


def print_banner(console: Console | None = None) -> None:
    if os.environ.get("ATELIER_NO_BANNER") == "1":
        return

    console = console or Console()
    console.print(_HAT, style="magenta", highlight=False)
    console.print(_WORDMARK, style="bold cyan", highlight=False)
    console.print(_TAGLINE, style="dim", highlight=False)
    console.print()
