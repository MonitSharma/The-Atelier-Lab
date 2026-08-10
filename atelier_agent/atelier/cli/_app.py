"""The Typer application object and its sub-apps.

Kept in its own module so every command module can import ``app`` without
importing its siblings — the package ``__init__`` is what pulls the command
modules in, so there is no cycle.
"""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    help="Atelier — a local research and coding workbench. Start with: ingest → ask.",
)
workspace_app = typer.Typer(help="Manage approved local workspace roots and capabilities.")
app.add_typer(workspace_app, name="workspace", rich_help_panel="Core setup")
repo_app = typer.Typer(help="Deterministic repository inspection and verification.")
app.add_typer(repo_app, name="repo", rich_help_panel="Core coding")
models_app = typer.Typer(help="Inspect configured models, local residency, and benchmarks.")
app.add_typer(models_app, name="models", rich_help_panel="Core setup")
project_app = typer.Typer(help="Manage explicit project-scoped memory.")
app.add_typer(project_app, name="project", hidden=True)
quantum_app = typer.Typer(help="Deterministic quantum-circuit inspection.")
app.add_typer(quantum_app, name="quantum", hidden=True)
optimize_app = typer.Typer(help="Deterministic optimization validation.")
app.add_typer(optimize_app, name="optimize", hidden=True)
state_app = typer.Typer(help="Initialize, validate, and migrate Atelier runtime state.")
app.add_typer(state_app, name="state", hidden=True)
finder_app = typer.Typer(help="Opt-in Finder/Shortcuts action plans.")
app.add_typer(finder_app, name="finder", hidden=True)
handoff_app = typer.Typer(help="Create explicit frontier-model handoff bundles.")
app.add_typer(handoff_app, name="handoff", hidden=True)
package_app = typer.Typer(help="Packaging and release-readiness checks.")
app.add_typer(package_app, name="package", hidden=True)
research_app = typer.Typer(help="Provenance-tracked external research operations.")
app.add_typer(research_app, name="research", hidden=True)
workflow_app = typer.Typer(help="Run durable typed workflows with checkpoints and approvals.")
app.add_typer(workflow_app, name="workflow", hidden=True)
security_app = typer.Typer(help="Manage explicit one-use destructive-operation confirmations.")
app.add_typer(security_app, name="security", hidden=True)
console = Console()
INGEST_PATHS_ARG = typer.Argument(None, help="Files or folders to index. Defaults to data/corpus.")
EVAL_PLOT_REPORT_OPT = typer.Option(None, "--report", help="Specific report JSON to plot.")
EVAL_PLOT_OUT_OPT = typer.Option(None, "--out", help="Directory for generated SVG plots.")
