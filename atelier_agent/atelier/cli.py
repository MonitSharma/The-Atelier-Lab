"""Atelier command-line interface.

    atelier doctor                 check models, store, and embeddings
    atelier ingest PATH...         index notes/PDFs/code into the vector store
    atelier ask "question"         grounded answer over your knowledge base
    atelier sources                list what's currently indexed
    atelier chat                   interactive knowledge-mode session

Run `python -m atelier.cli ...` if you haven't `pip install -e .`'d the package.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from atelier.config import settings

app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    help="Atelier — local research workbench.",
)
workspace_app = typer.Typer(help="Manage approved local workspace roots and capabilities.")
app.add_typer(workspace_app, name="workspace")
repo_app = typer.Typer(help="Deterministic repository inspection and verification.")
app.add_typer(repo_app, name="repo")
models_app = typer.Typer(help="Inspect configured models, local residency, and benchmarks.")
app.add_typer(models_app, name="models")
console = Console()
INGEST_PATHS_ARG = typer.Argument(None, help="Files or folders to index. Defaults to data/corpus.")
EVAL_PLOT_REPORT_OPT = typer.Option(None, "--report", help="Specific report JSON to plot.")
EVAL_PLOT_OUT_OPT = typer.Option(None, "--out", help="Directory for generated SVG plots.")


@workspace_app.command("add")
def workspace_add(
    path: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    name: str | None = typer.Option(None, "--name", help="Stable workspace name."),
    capabilities: str = typer.Option(
        "read", "--capabilities", help="Comma-separated: read,write,execute,network."
    ),
    privacy: str = typer.Option("LOCAL_ONLY", "--privacy", help="LOCAL_ONLY or CLOUD_ALLOWED."),
) -> None:
    """Approve a directory as an Atelier workspace without opening it."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    requested = {item.strip() for item in capabilities.split(",") if item.strip()}
    try:
        workspace = get_workspace_manager().add(
            path, name=name, capabilities=requested, privacy=privacy.upper()
        )
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(
        f"[green]Approved[/] {workspace.name}: {workspace.root} "
        f"({', '.join(sorted(workspace.capabilities))}; {workspace.privacy})"
    )


@workspace_app.command("open")
def workspace_open(name: str = typer.Argument(...)) -> None:
    """Attach a workspace and make it the active relative-path root."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        workspace = get_workspace_manager().open(name)
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(f"[green]Open[/] {workspace.name}: {workspace.root}")


@workspace_app.command("close")
def workspace_close(name: str = typer.Argument(...)) -> None:
    """Detach a workspace; its approval remains in the registry."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        workspace = get_workspace_manager().close(name)
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    console.print(f"[yellow]Closed[/] {workspace.name}")


@workspace_app.command("list")
def workspace_list() -> None:
    """List approved workspaces, attachment state, capabilities, and privacy."""
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        manager = get_workspace_manager()
        active = manager.active().name
        workspaces = manager.list()
    except WorkspaceError as exc:
        active = ""
        workspaces = get_workspace_manager().list()
        console.print(f"[yellow]{exc}[/]")
    table = Table(title="Approved Atelier workspaces")
    table.add_column("Name", style="bold")
    table.add_column("Root")
    table.add_column("State")
    table.add_column("Capabilities")
    table.add_column("Privacy")
    for workspace in workspaces:
        state = "active" if workspace.name == active else ("open" if workspace.attached else "closed")
        table.add_row(
            workspace.name,
            str(workspace.root),
            state,
            ", ".join(sorted(workspace.capabilities)),
            workspace.privacy,
        )
    console.print(table)


def _approved_repo_path(path: Path, capability: str = "read") -> Path:
    from atelier.workspace import WorkspaceError, get_workspace_manager

    try:
        return get_workspace_manager().context().resolve(str(path), capability).path
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc


def _repository(path: Path, capability: str = "read"):
    from repo.inspector import RepositoryInspector

    return RepositoryInspector.for_path(_approved_repo_path(path, capability))


@repo_app.command("inspect")
def repo_inspect(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    as_json: bool = typer.Option(False, "--json", help="Print the complete JSON profile."),
) -> None:
    """Characterize a repository without model calls or source embedding."""
    inspector = _repository(path)
    profile = inspector.inspect()
    if as_json:
        console.print_json(json.dumps(profile, default=str))
        return
    git = profile["git"]["status"]
    table = Table(title=f"Repository: {profile['root']}")
    table.add_column("Dimension", style="bold")
    table.add_column("Finding")
    table.add_row("Git", "not a Git repository" if not git["is_git"] else f"{git['branch']} · {'clean' if git['clean'] else 'changes'}")
    table.add_row("Files", f"{profile['file_count']}" + (" (truncated)" if profile["truncated"] else ""))
    table.add_row("Languages", ", ".join(f"{name} {count}" for name, count in profile["languages"].items()) or "none")
    table.add_row("Packages", ", ".join(item["manager"] for item in profile["package_managers"]) or "none detected")
    table.add_row("Environments", ", ".join(item["language"] for item in profile["environments"]) or "none detected")
    table.add_row("Tests", ", ".join(item["framework"] for item in profile["test_frameworks"]) or "none detected")
    table.add_row("Entry points", str(len(profile["entry_points"])))
    table.add_row("Symbols", str(sum(len(item["symbols"]) for item in profile["symbols"])))
    table.add_row("Test links", str(len(profile["test_relationships"])))
    console.print(table)
    if profile["important_files"]:
        console.print("[bold]Important files:[/] " + ", ".join(item["file"] for item in profile["important_files"][:12]))


@repo_app.command("status")
def repo_status(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)) -> None:
    """Show Git branch, cleanliness, changed paths, and recent history."""
    inspector = _repository(path)
    payload = {"status": inspector.git_status(), "history": inspector.git_history(), "diff": inspector.git_diff()}
    console.print_json(json.dumps(payload, default=str))


@repo_app.command("symbols")
def repo_symbols(path: Path = typer.Argument(Path("."), exists=True, file_okay=False)) -> None:
    """List deterministic symbols and imports without executing source code."""
    rows = _repository(path).symbols()
    for row in rows:
        console.print(f"[bold]{row['file']}[/] ({row['language']})")
        for symbol in row["symbols"]:
            console.print(f"  {symbol['kind']} {symbol['name']} : line {symbol['line']}")
        if row["imports"]:
            console.print("  imports: " + ", ".join(row["imports"]))


@repo_app.command("search")
def repo_search(
    pattern: str = typer.Argument(..., help="Regular expression to search."),
    path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
) -> None:
    """Search repository text deterministically and return file/line evidence."""
    from repo.inspector import RepositoryInspectionError

    try:
        hits = _repository(path).search(pattern)
    except RepositoryInspectionError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc
    table = Table(title=f"Repository search: {pattern}")
    table.add_column("File")
    table.add_column("Line")
    table.add_column("Text")
    for hit in hits:
        table.add_row(hit["file"], str(hit["line"]), hit["text"])
    console.print(table)


@repo_app.command("tests")
def repo_tests(
    path: Path = typer.Argument(Path("."), exists=True, file_okay=False),
    run: bool = typer.Option(False, "--run", help="Run the detected primary test command."),
) -> None:
    """Detect test frameworks and optionally run the primary local test command."""
    inspector = _repository(path, "execute" if run else "read")
    frameworks = inspector.test_frameworks()
    if not frameworks:
        console.print("[yellow]No supported test framework detected.[/]")
        return
    table = Table(title="Detected repository tests")
    table.add_column("Framework")
    table.add_column("Command")
    table.add_column("Tests")
    for framework in frameworks:
        table.add_row(framework["framework"], framework.get("command", ""), str(len(framework.get("tests", []))))
    console.print(table)
    if not run:
        return
    command = frameworks[0].get("command")
    if not command:
        console.print("[yellow]No runnable command was detected.[/]")
        return
    if command.startswith("python -m pytest"):
        command_args = [sys.executable, "-m", "pytest", "-q"]
    else:
        command_args = command.split()
    result = subprocess.run(command_args, cwd=str(inspector.root), text=True, capture_output=True, check=False)
    console.print(Text((result.stdout + "\n" + result.stderr).strip()[-12000:]))
    if result.returncode:
        raise typer.Exit(code=result.returncode)


@app.command("profile")
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


@app.command("paper-visual")
def paper_visual(
    path: Path = typer.Argument(..., exists=True, readable=True),
    render: bool = typer.Option(False, "--render", help="Render every page instead of fallback pages only."),
    as_json: bool = typer.Option(False, "--json", help="Print the complete page evidence JSON."),
) -> None:
    """Analyze PDF text quality and figure/caption pages with citations."""
    from atelier.workspace import WorkspaceError, get_workspace_manager
    from rag.visual import analyze_pdf

    try:
        approved = get_workspace_manager().context().resolve(str(path), "read").path
        report = analyze_pdf(approved, render=render)
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


@app.callback()
def _root(ctx: typer.Context) -> None:
    """Enter the Atelier workbench when no subcommand is supplied."""
    if ctx.invoked_subcommand is None:
        from atelier.session import run_session

        run_session(console)


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
        from rag.store import VectorStore
        from rag.manifest import IndexManifest

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
    """Incrementally index notes/PDFs/code into the local vector store."""
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
    from rag.retrieve import retrieve
    from rag.compat import IndexCompatibilityError

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
        console.print(Panel(Text(hit["text"]), title=Text(title), border_style="blue"))


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
    from rag.retrieve import format_context
    from rag.compat import IndexCompatibilityError

    role = "heavy" if heavy else "brain"
    try:
        with console.status(f"Retrieving + reasoning ({settings.heavy_model if heavy else settings.brain_model})..."):
            result = answer_question(question, k=k, role=role)
    except IndexCompatibilityError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc

    if show_context and result.hits:
        console.print(Panel(Text(format_context(result.hits)), title="Retrieved context", border_style="blue"))
    console.print(Panel(Text(result.text), title="Answer", border_style="green"))
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
        console.print(Panel(Text(result.text), border_style="green"))
        if result.sources:
            console.print("[dim]Sources: " + ", ".join(result.sources) + "[/]")


@app.command()
def agent(
    goal: str = typer.Argument(..., help="The task for the agent to accomplish."),
    heavy: bool = typer.Option(False, "--heavy", help="Use the heavy reasoning model."),
    shell: bool = typer.Option(False, "--shell", help="Allow the (powerful) shell tool."),
    memory: bool = typer.Option(False, "--memory", help="Recall relevant long-term memories first."),
    max_steps: int = typer.Option(10, "--max-steps", help="Max reasoning/tool steps."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Stream each step."),
) -> None:
    """Run the full dual-mode agent (knowledge + build) on a task."""
    from agent.react import ReActAgent
    from tools.registry import create_default_registry
    from atelier.workspace import get_workspace_manager

    role = "heavy" if heavy else "brain"

    def on_event(ev: dict) -> None:
        kind = ev.get("kind")
        if kind == "tool_call":
            console.print(f"[cyan]→ step {ev['step']}[/] [bold]{ev['tool']}[/] "
                          f"[dim]{ev.get('thought', '')}[/]")
        elif kind == "observation":
            color = "green" if ev.get("status") == "success" else "red"
            console.print(f"  [{color}]observed: {ev.get('status')}[/] from {ev.get('tool')}")
        elif kind == "parse_error":
            console.print(f"  [yellow]reflect: bad output — {ev.get('detail')}[/]")

    registry = create_default_registry(
        include_shell=shell,
        workspace=get_workspace_manager().context(),
    )
    runner = ReActAgent(registry, role=role, max_steps=max_steps,
                        verbose=False, on_event=on_event if verbose else None,
                        use_memory=memory)
    with console.status("Atelier is working..."):
        result = runner.run(goal)

    if result.success:
        console.print(Panel(Text(result.answer or ""), title=f"Done in {result.steps} steps",
                            border_style="green"))
    else:
        console.print(Panel(f"Did not finish within {result.steps} steps.",
                            title="Incomplete", border_style="red"))
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")


@app.command("code-fix")
def code_fix(
    goal: str = typer.Argument(..., help="Coding task to complete."),
    path: Path = typer.Option(Path("."), "--path", exists=True, file_okay=False),
    escalation: bool = typer.Option(True, "--escalate/--no-escalate", help="Retry with the brain role if the coder fails."),
    rollback: bool = typer.Option(False, "--rollback-on-failure", help="Restore workflow edits if the final certificate fails."),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
    as_json: bool = typer.Option(False, "--json", help="Print the complete certificate JSON."),
) -> None:
    """Run the typed inspect → edit → test → certificate coding workflow."""
    from atelier.coding_workflow import BuildWorkflow
    from atelier.workspace import WorkspaceError, get_workspace_manager

    manager = get_workspace_manager()
    try:
        context = manager.context()
        repository = context.resolve(str(path), "execute").path
    except WorkspaceError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=2) from exc

    with console.status("Running certified coding workflow..."):
        result = BuildWorkflow(repository, workspace=context).run(
            goal,
            role="coder",
            escalation_role="brain" if escalation else None,
            max_steps=max_steps,
            rollback_on_failure=rollback,
        )
    certificate = result.certificate.to_dict()
    if as_json:
        console.print_json(json.dumps(certificate, default=str))
    else:
        table = Table(title="Build Agent v2 certificate")
        table.add_column("Stage")
        table.add_column("Status")
        table.add_column("Evidence")
        for stage in result.certificate.stages:
            color = {"passed": "green", "failed": "red", "skipped": "yellow"}[stage.status]
            table.add_row(stage.name, f"[{color}]{stage.status}[/]", stage.detail[:180])
        console.print(table)
        console.print(
            f"Certificate: [{'green' if result.accepted else 'red'}]"
            f"{'accepted' if result.accepted else 'rejected'}[/] · "
            f"attempts={result.certificate.attempts} · "
            f"changed={len(result.certificate.changed_files)}"
        )
    if not result.accepted:
        raise typer.Exit(code=1)


@app.command()
def eval(
    mode: str = typer.Option("all", "--mode", help="all | docqa | code | combined"),
    judge: bool = typer.Option(False, "--judge", help="Add the local LLM-as-judge (slower)."),
    gate: bool = typer.Option(False, "--gate", help="Fail (exit 1) if any metric regressed vs the last report."),
) -> None:
    """Run the reliability eval suites and print + save a report."""
    from eval.run_eval import compare_reports, latest_report, run_all, save_report

    prev = latest_report() if gate else None

    with console.status(f"Running eval ({mode})... this calls the local model, be patient."):
        report = run_all(mode=mode, judge=judge)
    path = save_report(report)

    if "docqa" in report:
        agg = report["docqa"]["aggregate"]
        t = Table(title="Knowledge mode (doc-QA)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("correct")
        t.add_column("retrieval")
        t.add_column("cited")
        for r in report["docqa"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""),
                f'{r["correct"]}', f'{r["retrieval_hit"]}', f'{r["cited"]}',
            )
        console.print(t)
        console.print(f"[bold]doc-QA[/] correct={agg['correct']:.0%}  "
                      f"retrieval_hit={agg['retrieval_hit']:.0%}  cited={agg['cited']:.0%}")

    if "code" in report:
        agg = report["code"]["aggregate"]
        t = Table(title="Build mode (code)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("scope")
        t.add_column("solved")
        t.add_column("steps")
        t.add_column("tool_errs")
        for r in report["code"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""), r.get("edit_scope", ""),
                f'{r["solved"]}', f'{r["steps"]}', f'{r["tool_errors"]}',
            )
        console.print(t)
        console.print(f"[bold]code[/] solved={agg['solved']:.0%}  "
                      f"avg_steps={agg['steps']:.1f}  avg_tool_errors={agg['tool_errors']:.1f}")

    if "combined" in report:
        agg = report["combined"]["aggregate"]
        t = Table(title="Combined mode (knowledge → build)")
        t.add_column("id")
        t.add_column("category")
        t.add_column("difficulty")
        t.add_column("solved")
        t.add_column("tests")
        t.add_column("search_notes")
        t.add_column("steps")
        for r in report["combined"]["rows"]:
            t.add_row(
                r["id"], r.get("category", ""), r.get("difficulty", ""),
                f'{r["solved"]}', f'{r["tests_passed"]}', f'{r["used_search_notes"]}',
                f'{r["steps"]}',
            )
        console.print(t)
        console.print(f"[bold]combined[/] solved={agg['solved']:.0%}  "
                      f"tests_passed={agg['tests_passed']:.0%}  "
                      f"used_search_notes={agg['used_search_notes']:.0%}  "
                      f"avg_steps={agg['steps']:.1f}")

    console.print(f"[dim]Report: {path}[/]")

    if gate:
        if prev is None:
            console.print("[yellow]Gate: no prior report to compare against — baseline saved.[/]")
        else:
            regressions = compare_reports(prev, report)
            if regressions:
                console.print(Panel(Text("\n".join(regressions)), title=Text("⚠ Regressions detected"),
                                    border_style="red"))
                raise typer.Exit(code=1)
            console.print("[green]Gate: no regressions vs. last report.[/]")


@app.command("benchmark-coding")
def benchmark_coding(
    models: list[str] | None = typer.Option(
        None, "--model", help="Candidate model ID; repeat for multiple candidates."
    ),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
) -> None:
    """Benchmark local coding candidates on frozen multi-file repositories."""
    from eval.coding_benchmark import run, save

    candidates = models or [
        name for name in (settings.coder_model, settings.brain_model, settings.worker_model)
        if name
    ]
    with console.status("Running coding benchmark; local models may take a while..."):
        report = run(candidates, max_steps=max_steps)
    path = save(report)
    table = Table(title="Coding specialist benchmark")
    table.add_column("Model")
    table.add_column("Solve")
    table.add_column("Unnecessary reads")
    table.add_column("Tool errors")
    table.add_column("Latency")
    for model, summary in report["by_model"].items():
        table.add_row(
            model,
            f"{summary['solve_rate']:.0%}",
            f"{summary['mean_unnecessary_reads']:.1f}",
            f"{summary['mean_tool_errors']:.1f}",
            f"{summary['mean_latency_s']:.1f}s",
        )
    console.print(table)
    console.print(f"Report: {path}")


@app.command("eval-plots")
def eval_plots(
    report: Path | None = EVAL_PLOT_REPORT_OPT,
    out: Path | None = EVAL_PLOT_OUT_OPT,
) -> None:
    """Generate SVG plots from a saved eval report."""
    from eval.plots import main

    try:
        paths = main(str(report) if report else None, str(out) if out else None)
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/]")
        raise typer.Exit(code=1) from exc

    table = Table(title="Eval plots")
    table.add_column("File")
    for path in paths:
        table.add_row(str(path))
    console.print(table)


@app.command("benchmark-retrieval")
def benchmark_retrieval(
    k: int = typer.Option(6, "-k", help="Number of passages per query."),
) -> None:
    """Run the local scientific retrieval benchmark without reasoning-model calls."""
    from eval.retrieval import run_local_retrieval_benchmark

    try:
        report = run_local_retrieval_benchmark(k=k)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Retrieval benchmark failed:[/] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"[bold]Retrieval hits:[/] {report['aggregate']['hits']}/{report['aggregate']['queries']}")
    console.print(f"[bold]Reference-dominated queries:[/] {report['aggregate']['reference_dominated_queries']}")
    console.print(f"[dim]Report: {report['output']}[/]")


@app.command()
def remember(
    text: str = typer.Argument(..., help="The fact to store in long-term memory."),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags."),
) -> None:
    """Store a durable fact (persists across sessions)."""
    from agent.memory import get_memory

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    mid = get_memory().remember(text, tag_list)
    console.print(f"[green]Remembered[/] [dim]({mid})[/]: {text}")


@app.command()
def recall(
    query: str = typer.Argument(..., help="What to recall."),
    k: int = typer.Option(5, "-k", help="How many memories to return."),
) -> None:
    """Search long-term memory by meaning."""
    from agent.memory import get_memory

    memories = get_memory().recall(query, k=k)
    if not memories:
        console.print("[yellow]No memories yet. Add one with `atelier remember`.[/]")
        return
    table = Table(title=f"Recalled for: {query}")
    table.add_column("score")
    table.add_column("memory")
    table.add_column("tags", style="dim")
    for m in memories:
        table.add_row(f"{m.score}", m.text, ", ".join(m.tags))
    console.print(table)


@app.command("memory-migrate")
def memory_migrate() -> None:
    """Back up and re-embed semantic memory into a compatible collection."""
    from agent.memory import migrate_memory

    with console.status("Backing up and migrating semantic memory..."):
        result = migrate_memory()
    table = Table(show_header=False)
    table.add_row("Facts before", str(result["before"]))
    table.add_row("Facts after", str(result["after"]))
    table.add_row("Backup", result["backup"])
    console.print(Panel(table, title="Memory migration complete", border_style="green"))


@app.command()
def memory() -> None:
    """List everything in long-term memory."""
    from agent.memory import get_memory

    mems = get_memory().all()
    if not mems:
        console.print("[yellow]Memory is empty.[/]")
        return
    table = Table(title=f"Long-term memory ({len(mems)} facts)")
    table.add_column("id", style="dim")
    table.add_column("memory")
    table.add_column("tags", style="dim")
    for m in mems:
        table.add_row(m.id, m.text, ", ".join(m.tags))
    console.print(table)


@app.command()
def route(
    task: str = typer.Argument(..., help="A task to classify and route."),
    backend: str = typer.Option("auto", "--backend", help="auto | finetuned | heuristic"),
) -> None:
    """Classify a task by capability and show the local route decision."""
    from agent.capability_router import CapabilityRouter

    r = CapabilityRouter(backend=backend)
    with console.status("Routing..."):
        decision = r.decide(task)
    color = "red" if decision.abstain else ("green" if decision.difficulty == "easy" else "yellow")
    console.print(Panel(
        Text(
            f"domain: {decision.domain}\nworkflow: {decision.workflow}\n"
            f"difficulty: {decision.difficulty}\nrole: {decision.role}\n"
            f"model: {decision.model or 'abstain'}\nmodality: {decision.modality}\n"
            f"privacy: {decision.privacy}\nnetwork: {decision.requires_network}\n"
            f"memory: {decision.use_memory}\nreason: {decision.reason}"
        ),
        title=Text("Router decision"), border_style=color))


@models_app.command("list")
def models_list() -> None:
    """List configured roles, capabilities, install state, and memory estimates."""
    from models.lifecycle import ModelLifecycle

    table = Table(title="Atelier model lifecycle")
    for column in ("Role", "Model", "Configured", "Installed", "Resident", "Memory est.", "Context", "Modality"):
        table.add_column(column)
    for record in ModelLifecycle().list():
        table.add_row(
            record.role, record.model_id or "—", "yes" if record.configured else "no",
            "yes" if record.installed else "no", "yes" if record.resident else "no",
            f"{record.memory_estimate_gb:g} GB" if record.memory_estimate_gb else "—",
            f"{record.context_tokens:,}" if record.context_tokens else "—", record.modality,
        )
    console.print(table)


@models_app.command("status")
def models_status(as_json: bool = typer.Option(False, "--json")) -> None:
    """Show Ollama installation and residency status for configured roles."""
    from models.lifecycle import ModelLifecycle

    payload = ModelLifecycle().status()
    if as_json:
        console.print_json(json.dumps(payload, default=str))
        return
    console.print_json(json.dumps(payload, default=str))


@models_app.command("bench")
def models_bench(
    model: str = typer.Option(..., "--model", help="Ollama model ID to benchmark."),
    max_steps: int = typer.Option(14, "--max-steps", min=1, max=40),
) -> None:
    """Run the frozen coding benchmark for one local model."""
    from models.lifecycle import ModelLifecycle

    with console.status(f"Benchmarking {model}..."):
        report = ModelLifecycle().bench(model, max_steps=max_steps)
    summary = report["by_model"][model]
    console.print(
        f"{model}: solve={summary['solve_rate']:.0%}, "
        f"latency={summary['mean_latency_s']:.1f}s, "
        f"tool_errors={summary['mean_tool_errors']:.1f}\n"
        f"Report: {report['report_path']}"
    )


@app.command()
def mcp(shell: bool = typer.Option(False, "--shell", help="Expose the shell tool too.")) -> None:
    """Run Atelier's tools as an MCP server (stdio). For MCP clients."""
    from atelier.mcp_server import main as mcp_main

    mcp_main(include_shell=shell)


@app.command(name="tools")
def list_tools(shell: bool = typer.Option(False, "--shell")) -> None:
    """List the tools the agent can use."""
    from tools.registry import create_default_registry

    registry = create_default_registry(include_shell=shell)
    table = Table(title="Agent tools")
    table.add_column("Tool", style="bold")
    table.add_column("Description")
    for tool in registry.list_tools():
        table.add_row(tool.name, tool.description)
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    app()
