"""Compact, decorative Atelier terminal identity."""

from __future__ import annotations

import os

from rich.align import Align
from rich.console import Console

_LOGO = r"""
            ✦
           ╱ ╲
          ╱   ╲
     ✧   ╱ ◇ A ╲   ✧
        ╱       ╲
       ╱_________╲
   .─────────────────.
  /   ·   ✦   ◇   ✦   \
 /_____________________\
"""

_WORDMARK = "A T E L I E R   L A B"
_RULE = "─────── ◈ ───────"
_TAGLINE = "local research atelier"


def print_banner(console: Console | None = None) -> None:
    if os.environ.get("ATELIER_NO_BANNER") == "1":
        return

    console = console or Console()
    console.print(Align.center(_LOGO), style="magenta", highlight=False)
    console.print(Align.center(_WORDMARK), style="bold cyan", highlight=False)
    console.print(Align.center(_RULE), style="dim magenta", highlight=False)
    console.print(Align.center(_TAGLINE), style="dim", highlight=False)
    console.print()
