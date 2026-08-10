"""Knowledge mode: ingest, search, ask, and chat over the local library."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from atelier.cli._app import (
    INGEST_PATHS_ARG,
    app,
    console,
)
from atelier.cli._ui import _retrieved_context_panels, _sync_console_width
from atelier.config import settings


@app.command()
def doctor() -> None:
    """Check that models, the vector store, and embeddings are healthy."""
    from agent.brain import health

    h = health()
    table = Table(title="Atelier doctor", show_header=True, header_style="bold")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    if h["ok"]:
        for role, info in h["roles"].items():
            if not info.get("configured", bool(info.get("model"))):
                table.add_row(f"model:{role}", "[dim]unconfigured[/]", "optional future slot")
                continue
            ok = info["pulled"]
            table.add_row(
                f"model:{role}",
                "[green]ok[/]" if ok else "[red]missing[/]",
                info["model"] + ("" if ok else "  (run: ollama pull " + info["model"] + ")"),
            )
    else:
        table.add_row("ollama", "[red]down[/]", h.get("error", "unreachable"))

    try:
        from rag.manifest import IndexManifest
        from rag.store import VectorStore

        store = VectorStore()
        state = IndexManifest().state()
        state_model = state.get("embedding_model", "unknown")
        state_dim = state.get("embedding_dimension") or str(store.embedding_dimension() or "unknown")
        current_ok = state_model in {"unknown", settings.embed_model} and state_dim in {"unknown", str(settings.embed_dimension)}
        status = "[green]compatible[/]" if current_ok else "[red]incompatible[/]"
        table.add_row("knowledge index", status,
                      f"{store.count()} chunks; {state_model}; {state_dim}D")
    except Exception as exc:  # noqa: BLE001
        table.add_row("knowledge index", "[red]error[/]", str(exc))

    try:
        from agent.memory import MemoryStore
        from rag.manifest import IndexManifest

        memory_store = MemoryStore()
        memory_state = IndexManifest(settings.memory_manifest_path).state()
        table.add_row("memory", "[green]ok[/]", f"{memory_store.count()} facts; "
                      f"{memory_state.get('embedding_model', 'unknown')}; "
                      f"{memory_state.get('embedding_dimension', 'unknown')}D")
    except Exception as exc:  # noqa: BLE001
        table.add_row("memory", "[red]error[/]", str(exc))
    metadata_count = len(list(settings.paper_metadata_dir.glob("*.json"))) if settings.paper_metadata_dir.exists() else 0
    extraction_count = len(list(settings.extracted_dir.glob("*.json"))) if settings.extracted_dir.exists() else 0
    table.add_row("paper metadata cache", "[green]ok[/]", str(metadata_count))
    table.add_row("extraction cache", "[green]ok[/]", str(extraction_count))
    table.add_row("embed model", "[yellow]configured[/]", f"{settings.embed_model} (expected {settings.embed_dimension}D)")
    try:
        from atelier.workspace import get_workspace_manager

        manager = get_workspace_manager()
        attached = [workspace.name for workspace in manager.list() if workspace.attached]
        active = manager.active().name
        table.add_row("workspaces", "[green]ok[/]", f"active={active}; attached={', '.join(attached)}")
    except Exception as exc:  # noqa: BLE001 - doctor should report, not crash
        table.add_row("workspaces", "[red]error[/]", str(exc))
    console.print(table)


@app.command()
def ingest(
    paths: list[str] = INGEST_PATHS_ARG,
    reset: bool = typer.Option(False, "--reset", help="Clear the store before indexing."),
    force: bool = typer.Option(False, "--force", help="Force extraction and re-embedding."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the plan without modifying local state."),
    sync: bool = typer.Option(False, "--sync", help="Reconcile files removed from the supplied roots."),
) -> None:
    """Incrementally index supported documents, notes, images, archives, and code."""
    from rag.ingest import bootstrap_manifest_from_store, build_plan, execute_plan
    from rag.manifest import IndexManifest
    from rag.store import VectorStore

    targets = paths or [str(settings.corpus_dir)]
    manifest = IndexManifest()
    store = VectorStore()
    if reset and dry_run:
        console.print("[red]--reset cannot be combined with --dry-run.[/]")
        raise typer.Exit(code=2)
    if reset:
        # This is deliberately explicit: ordinary ingestion never destroys
        # records or manifest state.
        store.reset()
        manifest.reset()
        console.print("[yellow]Store reset.[/]")
    else:
        bootstrap_manifest_from_store(manifest, store, targets)
        # A development-era migration can preserve the SQLite manifest while
        # losing an untracked Chroma database.  Never treat that combination
        # as a clean no-op: rebuild the vectors from the manifest's source
        # files, preserving the manifest until each file is successfully
        # replaced by ``execute_plan``.
        if store.count() == 0 and manifest.all() and not force:
            force = True
            console.print(
                "[yellow]The manifest contains documents but the vector index is empty; "
                "rebuilding the local index.[/]"
            )
    plan = build_plan(targets, manifest, force=force, sync=sync)
    counts = plan.counts()
    table = Table(show_header=False)
    for key in ("unchanged", "new", "modified", "relocated", "duplicate", "forced", "removed"):
        table.add_row(key, str(counts.get(key, 0)))
    if dry_run:
        console.print(Panel(table, title="Ingest plan (dry run)", border_style="blue"))
        return
    changed = sum(counts.get(key, 0) for key in ("new", "modified", "forced"))
    if changed:
        from rag.embed import get_embedder

        embedder = get_embedder()
        with console.status(f"Extracting and embedding {changed} file(s) with {settings.embed_model}..."):
            execute_plan(plan, manifest, store, embedder)
        table.add_row("vector_dimension", str(getattr(embedder, "dim", "unknown")))
    else:
        execute_plan(plan, manifest, store, embedder=None)
    table.add_row("chunks_in_index", str(store.count()))
    console.print(Panel(table, title="Ingest complete", border_style="green"))


@app.command()
def search(
    query: str = typer.Argument(..., help="Scientific or general retrieval query."),
    k: int = typer.Option(settings.retrieval_k, "-k", help="How many passages to show."),
    source: str | None = typer.Option(None, "--source", help="Restrict to a filename."),
    section_type: str | None = typer.Option(None, "--section-type", help="Restrict to section type."),
    debug: bool = typer.Option(False, "--debug", "--scores", help="Show ranking diagnostics."),
) -> None:
    """Show the most relevant passages without model synthesis."""
    from rag.compat import IndexCompatibilityError
    from rag.retrieve import retrieve

    _sync_console_width()
    try:
        with console.status("Searching the local research library..."):
            hits = retrieve(query, k=k, source=source, section_type=section_type)
    except IndexCompatibilityError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    if not hits:
        console.print("[yellow]No matching passages. Run `atelier ingest <path>` first.[/]")
        return
    for i, hit in enumerate(hits, start=1):
        meta = hit.get("metadata", {})
        source = Path(meta.get("source", "?")).name
        section = meta.get("section", "")
        label = f"{source}  {section}" if section else source
        title = f"[{i}] {label}"
        if debug:
            title += f"  score={hit.get('final_score', hit.get('score', 0)):.4f}"
            title += f" adj={hit.get('section_adjustment', 1.0):.2f}"
        console.print(
            Panel(
                Text(hit["text"], overflow="fold", no_wrap=False),
                title=Text(title),
                border_style="blue",
                expand=True,
                padding=(0, 1),
            )
        )


@app.command()
def paper(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Research PDF to characterize."),
    index: bool = typer.Option(False, "--ingest", help="Also index the full paper after characterization."),
) -> None:
    """Create a cached Fast Paper characterization card for a research PDF."""
    from rag.paper import characterize

    if path.suffix.lower() != ".pdf":
        console.print("[red]Input must be a PDF.[/]")
        raise typer.Exit(code=2)
    with console.status(f"Characterizing {path.name} with {settings.worker_model}..."):
        result = characterize(path)
    console.print_json(json.dumps(result, ensure_ascii=False))
    console.print(f"[dim]Cached under {settings.paper_metadata_dir}[/]")
    if index:
        ingest(paths=[str(path)], reset=False)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your question."),
    k: int = typer.Option(settings.retrieval_k, "-k", help="How many chunks to retrieve."),
    show_context: bool = typer.Option(False, "--show-context", help="Print retrieved passages."),
    heavy: bool = typer.Option(False, "--heavy", help="Use the heavy reasoning model."),
) -> None:
    """Answer a question grounded in your indexed knowledge."""
    from rag.answer import answer_question
    from rag.compat import IndexCompatibilityError

    _sync_console_width()
    role = "heavy" if heavy else "brain"
    try:
        with console.status(f"Retrieving + reasoning ({settings.heavy_model if heavy else settings.brain_model})..."):
            result = answer_question(question, k=k, role=role)
    except IndexCompatibilityError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc

    if show_context and result.hits:
        console.print(f"[bold blue]Retrieved context · {len(result.hits)} passages[/]")
        for context_panel in _retrieved_context_panels(result.hits, width=console.width):
            console.print(context_panel)
    console.print(
        Panel(
            Text(result.text, overflow="fold", no_wrap=False),
            title="Answer",
            border_style="green",
            expand=True,
            padding=(0, 1),
        )
    )
    if result.sources:
        console.print("[dim]Sources: " + ", ".join(result.sources) + "[/]")


@app.command()
def sources() -> None:
    """List the source files currently in the knowledge base."""
    from rag.store import VectorStore

    store = VectorStore()
    srcs = store.sources()
    if not srcs:
        console.print("[yellow]Knowledge base is empty. Run `atelier ingest <path>`.[/]")
        return
    table = Table(title=f"Indexed sources ({len(srcs)})")
    table.add_column("File")
    for s in srcs:
        table.add_row(Path(s).name + f"  [dim]{s}[/]")
    console.print(table)


@app.command()
def chat(
    heavy: bool = typer.Option(False, "--heavy", help="Use the heavy reasoning model."),
) -> None:
    """Interactive knowledge-mode session (Ctrl-D / 'exit' to quit)."""
    from rag.answer import answer_question

    _sync_console_width()
    role = "heavy" if heavy else "brain"
    console.print(Panel("Atelier knowledge chat. Ask about your notes. 'exit' to quit.", border_style="cyan"))
    while True:
        try:
            q = console.input("[bold cyan]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]bye[/]")
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        with console.status("thinking..."):
            result = answer_question(q, role=role)
        _sync_console_width()
        console.print(
            Panel(
                Text(result.text, overflow="fold", no_wrap=False),
                border_style="green",
                expand=True,
                padding=(0, 1),
            )
        )
        if result.sources:
            console.print("[dim]Sources: " + ", ".join(result.sources) + "[/]")
