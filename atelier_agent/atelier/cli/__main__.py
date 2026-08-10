"""Entry point for ``python -m atelier.cli``.

A package cannot be executed directly the way the old single-module ``cli.py``
could, so this restores that invocation — it is what the Makefile, the
interactive session's re-exec, and the README all use.
"""

from __future__ import annotations

from atelier.cli import app

app()
