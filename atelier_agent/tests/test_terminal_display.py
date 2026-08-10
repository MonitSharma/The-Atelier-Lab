from io import StringIO
import os

from rich.console import Console

from atelier.cli import _retrieved_context_panels, _sync_console_width


def test_console_width_refreshes_from_current_terminal(monkeypatch) -> None:
    console = Console(width=80, file=StringIO())
    monkeypatch.setattr(
        "atelier.cli.shutil.get_terminal_size",
        lambda fallback: os.terminal_size((160, 40)),
    )

    _sync_console_width(console)

    assert console.width == 160


def test_retrieved_context_cards_fill_a_wide_console() -> None:
    output = StringIO()
    console = Console(width=120, file=output, no_color=True)
    hits = [
        {
            "text": "A useful passage that should wrap to the available terminal width.",
            "metadata": {"source": "/tmp/notes.md", "page": 3, "section": "Wetlands"},
        }
    ]

    for panel in _retrieved_context_panels(hits, width=console.width):
        console.print(panel)

    lines = output.getvalue().splitlines()
    assert any(len(line) == 120 for line in lines)
    assert "notes.md" in output.getvalue()
    assert "p. 3" in output.getvalue()
