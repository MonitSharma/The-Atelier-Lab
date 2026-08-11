"""Provenance-tracked research lookups, papers, and artifact profiling."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.markdown import Markdown
from rich.table import Table

from atelier.cli._app import (
    app,
    console,
    research_app,
)


@app.command("profile", hidden=True)
def profile_artifact(
    path: Path = typer.Argument(..., exists=True, readable=True),
    as_json: bool = typer.Option(False, "--json", help="Print the complete artifact profile."),
) -> None:
    """Profile a structured file deterministically before model reasoning."""
    from atelier.workspace import WorkspaceError, get_workspace_manager
    from files.artifacts import profile_path

    try:
        approved = get_workspace_manager().context().resolve(str(path), "read").path
        profile = profile_path(approved).to_dict()
    except (WorkspaceError, ValueError, OSError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    if as_json:
        console.print_json(json.dumps(profile, default=str))
        return
    table = Table(title=f"Artifact profile: {approved.name}")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    for field in ("kind", "size_bytes", "shape", "schema", "missingness", "formulas", "references", "warnings"):
        table.add_row(field, json.dumps(profile[field], default=str)[:4000])
    console.print(table)


@app.command("paper-visual", hidden=True)
def paper_visual(
    path: Path = typer.Argument(..., exists=True, readable=True),
    render: bool = typer.Option(False, "--render", help="Render every page instead of fallback pages only."),
    ocr: bool = typer.Option(False, "--ocr", help="Attempt opt-in OCR for poor-text pages; native text remains authoritative."),
    as_json: bool = typer.Option(False, "--json", help="Print the complete page evidence JSON."),
) -> None:
    """Analyze PDF text quality and figure/caption pages with citations."""
    from atelier.workspace import WorkspaceError, get_workspace_manager
    from rag.visual import analyze_pdf

    try:
        approved = get_workspace_manager().context().resolve(str(path), "read").path
        report = analyze_pdf(approved, render=render, ocr=ocr)
    except (WorkspaceError, ValueError, OSError, RuntimeError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    if as_json:
        console.print_json(json.dumps(report, default=str))
        return
    table = Table(title=f"Visual evidence: {approved.name}")
    table.add_column("Page")
    table.add_column("Quality")
    table.add_column("Characters")
    table.add_column("Figures")
    table.add_column("Citation")
    for page in report["pages"]:
        table.add_row(str(page["page"]), page["quality"], str(page["characters"]), str(len(page["captions"])), page["citation"])
    console.print(table)
    console.print(f"Visual fallback needed: {'yes' if report['visual_fallback'] else 'no'}")


@app.command("research-lookup", hidden=True)
def research_lookup(
    query: str | None = typer.Argument(None, help="Explicit bibliographic query."),
    source: str = typer.Option("crossref", "--source", help="crossref, arxiv, or semantic_scholar."),
    doi: str | None = typer.Option(None, "--doi", help="Explicit DOI for a Crossref lookup."),
    max_results: int = typer.Option(5, "--max-results", min=1, max=20),
) -> None:
    """Run a provenance-tracked external lookup under the active privacy policy."""
    from atelier.workspace import WorkspaceError, get_workspace_manager, workspace_scope
    from tools.research import run_research_lookup

    try:
        context = get_workspace_manager().context()
        with workspace_scope(context):
            result = run_research_lookup({
                "query": query, "source": source, "doi": doi, "max_results": max_results,
            })
    except WorkspaceError as exc:
        result = {"status": "denied", "error_type": "network_denied", "message": str(exc)}
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


def _run_research_operation(operation: str, arguments: dict[str, object]) -> None:
    from atelier.workspace import WorkspaceError, get_workspace_manager, workspace_scope
    from tools.research import download_paper, research_graph, verify_citation

    try:
        context = get_workspace_manager().context()
        with workspace_scope(context):
            if operation == "graph":
                result = research_graph(arguments)
            elif operation == "verify-citation":
                result = verify_citation(arguments)
            else:
                result = download_paper(arguments)
    except WorkspaceError as exc:
        result = {"status": "denied", "error_type": "workspace_denied", "message": str(exc)}
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


@research_app.command("graph")
def research_graph_command(
    paper_id: str | None = typer.Option(None, "--paper-id"),
    doi: str | None = typer.Option(None, "--doi"),
    relation: str = typer.Option("related", "--relation", help="related or cited_by"),
    max_results: int = typer.Option(10, "--max-results", min=1, max=100),
) -> None:
    """Find related papers or papers citing an explicit paper identifier."""
    _run_research_operation("graph", {"paper_id": paper_id, "doi": doi, "relation": relation, "max_results": max_results})


@research_app.command("verify-citation")
def research_verify_citation(
    doi: str = typer.Option(..., "--doi"),
    title: str = typer.Option(..., "--title"),
    authors: str = typer.Option("", "--authors", help="Comma-separated author family names."),
) -> None:
    """Compare a citation against Crossref metadata."""
    _run_research_operation("verify-citation", {"doi": doi, "title": title, "authors": [item.strip() for item in authors.split(",") if item.strip()]})


@research_app.command("download")
def research_download(
    url: str = typer.Option(..., "--url"),
    destination: str = typer.Option(..., "--destination"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    """Download an explicitly selected paper into the active cloud-approved workspace."""
    _run_research_operation("download", {"url": url, "destination": destination, "overwrite": overwrite})


def _run_web_operation(operation: str, arguments: dict[str, object]) -> None:
    from atelier.workspace import WorkspaceError, get_workspace_manager, workspace_scope
    from tools.web_research import fetch_webpage, search_web

    try:
        context = get_workspace_manager().context()
        with workspace_scope(context):
            result = search_web(arguments) if operation == "search" else fetch_webpage(arguments)
    except WorkspaceError as exc:
        result = {"status": "denied", "error_type": "workspace_denied", "message": str(exc)}
    console.print_json(json.dumps(result, default=str))
    if result.get("status") != "success":
        raise typer.Exit(code=2)


@research_app.command("web-search")
def research_web_search(
    query: str = typer.Argument(...),
    max_results: int = typer.Option(5, "--max-results", min=1, max=10),
) -> None:
    """Search the general web through the bounded no-key provider."""
    _run_web_operation("search", {"query": query, "max_results": max_results})


@research_app.command("fetch")
def research_fetch_webpage(
    url: str = typer.Argument(...),
    max_chars: int = typer.Option(20_000, "--max-chars", min=500, max=50_000),
    max_bytes: int = typer.Option(2_000_000, "--max-bytes", min=1_000, max=5_000_000),
) -> None:
    """Safely fetch and extract one public HTTPS webpage."""
    _run_web_operation("fetch", {
        "url": url, "max_chars": max_chars, "max_bytes": max_bytes,
    })


@app.command("deep-research")
@research_app.command("deep")
def deep_research_command(
    question: str = typer.Argument(..., help="Research question to investigate."),
    depth: str = typer.Option("standard", "--depth", help="quick, standard, or deep."),
    sources: str = typer.Option(
        "web,semantic_scholar,arxiv,crossref", "--sources",
        help="Comma-separated web and scholarly providers.",
    ),
    max_rounds: int | None = typer.Option(None, "--max-rounds", min=1, max=5),
    max_sources: int | None = typer.Option(None, "--max-sources", min=3, max=60),
    max_web_pages: int | None = typer.Option(None, "--max-web-pages", min=0, max=30),
    verify_dois: bool = typer.Option(False, "--verify-dois", help="Recheck up to ten DOI records against Crossref."),
    model_free: bool = typer.Option(False, "--model-free", help="Exercise deterministic orchestration without synthesis."),
    project: str = typer.Option("default", "--project"),
    as_json: bool = typer.Option(False, "--json", help="Print the complete persisted workflow state."),
) -> None:
    """Run bounded iterative research, counter-search, synthesis, and citation checks."""
    from atelier.service import AtelierService
    from atelier.workspace import WorkspaceError, get_workspace_manager

    selected_sources = [item.strip() for item in sources.split(",") if item.strip()]
    try:
        result = AtelierService(manager=get_workspace_manager()).deep_research(
            question,
            depth=depth,
            project=project,
            sources=selected_sources,
            max_rounds=max_rounds,
            max_sources=max_sources,
            max_web_pages=max_web_pages,
            verify_dois=verify_dois,
            model_free=model_free,
        )
    except (KeyError, TypeError, ValueError, WorkspaceError) as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    if as_json or result.get("status") != "completed":
        console.print_json(json.dumps(result, default=str))
    else:
        report = result.get("outputs", {}).get("verify report", {}).get("report_markdown")
        if isinstance(report, str):
            console.print(Markdown(report))
        else:
            console.print_json(json.dumps(result, default=str))
    if result.get("status") == "failed":
        raise typer.Exit(code=2)
