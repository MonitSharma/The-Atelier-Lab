"""Generate dependency-free SVG plots from saved eval reports.

Usage:
    python -m eval.plots
    python -m eval.plots data/eval_reports/report_YYYYMMDDTHHMMSS.json

The plots are intentionally simple and stdlib-only so the eval story stays
fully local and reproducible without adding a plotting dependency.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from atelier.config import settings
from eval.run_eval import latest_report

PALETTE = {
    "green": "#16a34a",
    "blue": "#2563eb",
    "amber": "#d97706",
    "red": "#dc2626",
    "slate": "#334155",
    "muted": "#e2e8f0",
    "text": "#0f172a",
    "subtle": "#64748b",
}


def _latest_report_path() -> Path | None:
    out_dir = settings.data_dir / "eval_reports"
    if not out_dir.exists():
        return None
    reports = sorted(out_dir.glob("report_*.json"))
    return reports[-1] if reports else None


def load_report(path: Path | None = None) -> tuple[dict[str, Any], Path | None]:
    """Load an explicit report path, or the latest saved report."""
    if path is not None:
        return json.loads(path.read_text()), path
    found = _latest_report_path()
    if found is None:
        report = latest_report()
        if report is None:
            raise FileNotFoundError("No eval reports found. Run `atelier eval --mode all` first.")
        return report, None
    return json.loads(found.read_text()), found


def _svg(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">\n'
        '<style>'
        'text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}'
        '.title{font-size:22px;font-weight:700;fill:#0f172a;}'
        '.label{font-size:13px;fill:#334155;}'
        '.small{font-size:12px;fill:#64748b;}'
        '</style>\n'
        f"{body}\n</svg>\n"
    )


def _bar_chart(title: str, rows: list[tuple[str, float]], *, color: str = "green") -> str:
    width = 920
    left = 260
    right = 70
    top = 72
    row_h = 44
    height = max(180, top + len(rows) * row_h + 44)
    chart_w = width - left - right
    parts = [
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<text x="32" y="38" class="title">{escape(title)}</text>',
    ]
    for idx, (label, value) in enumerate(rows):
        y = top + idx * row_h
        pct = max(0.0, min(1.0, value))
        bar_w = chart_w * pct
        parts.append(f'<text x="32" y="{y + 22}" class="label">{escape(label)}</text>')
        parts.append(
            f'<rect x="{left}" y="{y}" width="{chart_w}" height="24" rx="4" fill="{PALETTE["muted"]}"/>'
        )
        parts.append(
            f'<rect x="{left}" y="{y}" width="{bar_w:.1f}" height="24" rx="4" fill="{PALETTE[color]}"/>'
        )
        parts.append(
            f'<text x="{left + chart_w + 12}" y="{y + 18}" class="small">{pct * 100:.0f}%</text>'
        )
    return _svg(width, height, "\n".join(parts))


def _latency_steps_chart(rows: list[dict[str, Any]]) -> str:
    width = 980
    height = max(240, 92 + len(rows) * 36 + 52)
    left = 260
    right = 64
    top = 74
    row_h = 36
    max_steps = max(float(r.get("steps") or 0) for r in rows) or 1
    chart_w = width - left - right
    parts = [
        f'<rect width="{width}" height="{height}" fill="white"/>',
        '<text x="32" y="38" class="title">Build Tasks: Steps and Outcome</text>',
        f'<text x="{left}" y="62" class="small">bar length = steps, color = solved</text>',
    ]
    for idx, row in enumerate(rows):
        y = top + idx * row_h
        steps = float(row.get("steps") or 0)
        solved = bool(row.get("solved"))
        fill = PALETTE["green"] if solved else PALETTE["red"]
        width_steps = chart_w * (steps / max_steps)
        label = f'{row["id"]} ({row.get("edit_scope", "?")})'
        parts.append(f'<text x="32" y="{y + 17}" class="label">{escape(label)}</text>')
        parts.append(
            f'<rect x="{left}" y="{y}" width="{chart_w}" height="20" rx="4" fill="{PALETTE["muted"]}"/>'
        )
        parts.append(f'<rect x="{left}" y="{y}" width="{width_steps:.1f}" height="20" rx="4" fill="{fill}"/>')
        parts.append(f'<text x="{left + chart_w + 12}" y="{y + 15}" class="small">{steps:.0f}</text>')
    return _svg(width, height, "\n".join(parts))


def _rows_from_group(group: dict[str, dict[str, float]], metric: str) -> list[tuple[str, float]]:
    return [(name, values.get(metric, 0.0)) for name, values in sorted(group.items())]


def generate_plots(report: dict[str, Any], output_dir: Path) -> list[Path]:
    """Write SVG plots for the modes present in a report and return paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if "docqa" in report:
        doc = report["docqa"]
        agg = doc.get("aggregate", {})
        overview = [
            ("Correct", agg.get("correct", 0.0)),
            ("Retrieval hit@k", agg.get("retrieval_hit", 0.0)),
            ("Cited sources", agg.get("cited", 0.0)),
        ]
        path = output_dir / "docqa_overview.svg"
        path.write_text(_bar_chart("Knowledge Mode: Overall Scores", overview, color="blue"))
        written.append(path)

        if doc.get("by_category"):
            path = output_dir / "docqa_by_category.svg"
            path.write_text(
                _bar_chart(
                    "Knowledge Mode: Correctness by Category",
                    _rows_from_group(doc["by_category"], "correct"),
                    color="blue",
                )
            )
            written.append(path)

    if "code" in report:
        code = report["code"]
        agg = code.get("aggregate", {})
        overview = [
            ("Solved", agg.get("solved", 0.0)),
            ("No tool errors", max(0.0, 1.0 - agg.get("tool_errors", 0.0))),
        ]
        path = output_dir / "code_overview.svg"
        path.write_text(_bar_chart("Build Mode: Overall Scores", overview, color="green"))
        written.append(path)

        if code.get("by_difficulty"):
            path = output_dir / "code_by_difficulty.svg"
            path.write_text(
                _bar_chart(
                    "Build Mode: Solved by Difficulty",
                    _rows_from_group(code["by_difficulty"], "solved"),
                    color="green",
                )
            )
            written.append(path)

        if code.get("by_edit_scope"):
            path = output_dir / "code_by_edit_scope.svg"
            path.write_text(
                _bar_chart(
                    "Build Mode: Solved by Edit Scope",
                    _rows_from_group(code["by_edit_scope"], "solved"),
                    color="amber",
                )
            )
            written.append(path)

        rows = code.get("rows", [])
        if rows:
            path = output_dir / "code_steps_by_task.svg"
            path.write_text(_latency_steps_chart(rows))
            written.append(path)

    if "combined" in report:
        combined = report["combined"]
        agg = combined.get("aggregate", {})
        overview = [
            ("Solved", agg.get("solved", 0.0)),
            ("Tests passed", agg.get("tests_passed", 0.0)),
            ("Used search_notes", agg.get("used_search_notes", 0.0)),
        ]
        path = output_dir / "combined_overview.svg"
        path.write_text(_bar_chart("Combined Mode: Knowledge to Build", overview, color="amber"))
        written.append(path)

        if combined.get("by_category"):
            path = output_dir / "combined_by_category.svg"
            path.write_text(
                _bar_chart(
                    "Combined Mode: Solved by Category",
                    _rows_from_group(combined["by_category"], "solved"),
                    color="amber",
                )
            )
            written.append(path)

    return written


def main(report_path: str | None = None, output_dir: str | None = None) -> list[Path]:
    report, path = load_report(Path(report_path) if report_path else None)
    base = Path(output_dir) if output_dir else settings.data_dir / "eval_reports" / "plots"
    if path is not None:
        base = base / path.stem
    return generate_plots(report, base)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("report", nargs="?", help="Path to a saved eval report JSON.")
    parser.add_argument("--out", help="Output directory for SVG plots.")
    args = parser.parse_args()

    for written in main(args.report, args.out):
        print(written)
