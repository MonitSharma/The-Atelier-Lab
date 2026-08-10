"""Terminal rendering helpers shared by the command modules."""

from __future__ import annotations

import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from atelier.cli._app import console


def _sync_console_width(target: Console = console) -> None:
    """Refresh Rich's width after a Terminal resize.

    Rich normally reads the terminal size lazily, but a ``COLUMNS`` value
    inherited when Atelier starts can pin the console to the old width. The
    interactive shell also stays alive across window resizes, so refresh the
    dimensions immediately before rendering command output.
    """
    try:
        columns = shutil.get_terminal_size(fallback=(80, 24)).columns
    except OSError:
        return
    if columns > 0:
        # Rich has no public setter for a live console width. Clearing the
        # cached height keeps terminal height dynamic while this updates the
        # width from the current window rather than stale COLUMNS metadata.
        target._width = columns  # type: ignore[attr-defined]
        target._height = None  # type: ignore[attr-defined]


def _retrieved_context_panels(hits: list[dict], *, width: int | None = None) -> list[Panel]:
    """Build full-width, independently readable retrieval cards."""
    panels: list[Panel] = []
    for i, hit in enumerate(hits, start=1):
        meta = hit.get("metadata", {})
        source = Path(meta.get("source", "?")).name
        location: list[str] = []
        if meta.get("source_date"):
            location.append(f"date: {meta['source_date']}")
        for key, label in (("page", "p."), ("slide", "slide"), ("table", "table")):
            if meta.get(key) is not None:
                location.append(f"{label} {meta[key]}")
        if meta.get("heading"):
            location.append(f"heading: {meta['heading']}")
        if meta.get("section"):
            location.append(f"section: {meta['section']}")
        if meta.get("speaker_notes"):
            location.append("speaker notes")
        if meta.get("image_member"):
            location.append(f"image: {meta['image_member']}")
        if meta.get("archive_member"):
            location.append(f"archive: {meta['archive_member']}")
        if meta.get("human_review"):
            location.append("HUMAN REVIEW FLAG")
        title = f"[{i}] {source}"
        if location:
            title += "  ·  " + "  ·  ".join(location)
        panels.append(
            Panel(
                Text(str(hit.get("text", "")), overflow="fold", no_wrap=False),
                title=Text(title),
                border_style="blue",
                expand=True,
                width=width,
                padding=(0, 1),
            )
        )
    return panels
