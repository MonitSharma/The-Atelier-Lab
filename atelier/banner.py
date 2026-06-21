"""The Atelier banner — a little magician's hat, because the name earns it.

Printed once per CLI invocation. Suppress with ``ATELIER_NO_BANNER=1`` (useful
when scripting or piping output).
"""

from __future__ import annotations

import os

from rich.console import Console

_HAT = r"""
              *  .   ✦   .  *
               _________
              |         |          ✦
              |  =====  |      .         *
            __|_________|__
           |_______________|      ~ poof! ✨
"""

_WORDMARK = r"""
     _   _____ _____ _     ___ _____ ____
    / \ |_   _| ____| |   |_ _| ____|  _ \
   / _ \  | | |  _| | |    | ||  _| | |_) |
  / ___ \ | | | |___| |___ | || |___|  _ <
 /_/   \_\|_| |_____|_____|___|_____|_| \_\
"""

_TAGLINE = "   a private, local magician — knowledge · build · $0 cloud"


def print_banner(console: Console | None = None) -> None:
    if os.environ.get("ATELIER_NO_BANNER") == "1":
        return
    console = console or Console()
    console.print(_HAT, style="magenta", highlight=False)
    console.print(_WORDMARK, style="bold cyan", highlight=False)
    console.print(_TAGLINE, style="dim", highlight=False)
    console.print()
