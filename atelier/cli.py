"""Atelier command-line interface.

    atelier doctor                 check models, store, and embeddings
    atelier ingest PATH...         index notes/PDFs/code into the vector store
    atelier ask "question"         grounded answer over your knowledge base
    atelier sources                list what's currently indexed
    atelier chat                   interactive knowledge-mode session

Run `python -m atelier.cli ...` if you haven't `pip install -e .`'d the package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from atelier.config import settings

app = typer.Typer(add_completion=False, help="Atelier — a local, zero-cost dual-mode agent.")
console = Console()


@app.callback()
def _root() -> None:
    """Show the banner before any command (set ATELIER_NO_BANNER=1 to hide)."""
    from atelier.banner import print_banner

    print_banner(console)


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

        store = VectorStore()
        table.add_row("vector store", "[green]ok[/]", f"{store.count()} chunks @ {settings.vector_dir}")
    except Exception as exc:  # noqa: BLE001
        table.add_row("vector store", "[red]error[/]", str(exc))

    table.add_row("embed model", "[yellow]lazy[/]", f"{settings.embed_model} on {settings.embed_device}")
    console.print(table)


@app.command()
def ingest(
    paths: list[str] = typer.Argument(None, help="Files or folders to index. Defaults to data/corpus."),
    reset: bool = typer.Option(False, "--reset", help="Clear the store before indexing."),
) -> None:
    """Index notes/PDFs/code into the local vector store."""
    from rag.embed import get_embedder
    from rag.ingest import ingest_paths
    from rag.store import VectorStore

    targets = paths or [str(settings.corpus_dir)]
    store = VectorStore()
    if reset:
        store.reset()
        console.print("[yellow]Store reset.[/]")

    with console.status("Loading and chunking files..."):
        chunks, files = ingest_paths(targets)
    if not chunks:
        console.print(
            Panel(
                f"No supported files found under: {', '.join(targets)}\n"
                "Point me at your notes, e.g.  atelier ingest ~/Notes",
                title="Nothing to ingest",
                border_style="yellow",
            )
        )
        raise typer.Exit(code=0)

    embedder = get_embedder()
    texts = [c.text for c in chunks]
    with console.status(f"Embedding {len(texts)} chunks with {settings.embed_model}..."):
        vectors = embedder.embed_passages(texts)
        n = store.add(chunks, vectors)

    table = Table(show_header=False)
    table.add_row("Files indexed", str(len(files)))
    table.add_row("Chunks stored", str(n))
    table.add_row("Total in store", str(store.count()))
    table.add_row("Vector dim", str(embedder.dim))
    console.print(Panel(table, title="Ingest complete", border_style="green"))


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

    role = "heavy" if heavy else "brain"
    with console.status(f"Retrieving + reasoning ({settings.heavy_model if heavy else settings.brain_model})..."):
        result = answer_question(question, k=k, role=role)

    if show_context and result.hits:
        console.print(Panel(format_context(result.hits), title="Retrieved context", border_style="blue"))
    console.print(Panel(result.text, title="Answer", border_style="green"))
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
        console.print(Panel(result.text, border_style="green"))
        if result.sources:
            console.print("[dim]Sources: " + ", ".join(result.sources) + "[/]")


@app.command()
def agent(
    goal: str = typer.Argument(..., help="The task for the agent to accomplish."),
    heavy: bool = typer.Option(False, "--heavy", help="Use the heavy reasoning model."),
    shell: bool = typer.Option(False, "--shell", help="Allow the (powerful) shell tool."),
    max_steps: int = typer.Option(10, "--max-steps", help="Max reasoning/tool steps."),
    verbose: bool = typer.Option(True, "--verbose/--quiet", help="Stream each step."),
) -> None:
    """Run the full dual-mode agent (knowledge + build) on a task."""
    from agent.react import ReActAgent
    from tools.registry import create_default_registry

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

    registry = create_default_registry(include_shell=shell)
    runner = ReActAgent(registry, role=role, max_steps=max_steps,
                        verbose=False, on_event=on_event if verbose else None)
    with console.status("Atelier is working..."):
        result = runner.run(goal)

    if result.success:
        console.print(Panel(result.answer or "", title=f"Done in {result.steps} steps",
                            border_style="green"))
    else:
        console.print(Panel(f"Did not finish within {result.steps} steps.",
                            title="Incomplete", border_style="red"))
    if result.trace_path:
        console.print(f"[dim]Trace: {result.trace_path}[/]")


@app.command()
def eval(
    mode: str = typer.Option("all", "--mode", help="all | docqa | code"),
    judge: bool = typer.Option(False, "--judge", help="Add the local LLM-as-judge (slower)."),
) -> None:
    """Run the reliability eval suites and print + save a report."""
    from eval.run_eval import run_all, save_report

    with console.status(f"Running eval ({mode})... this calls the local model, be patient."):
        report = run_all(mode=mode, judge=judge)
    path = save_report(report)

    if "docqa" in report:
        agg = report["docqa"]["aggregate"]
        t = Table(title="Knowledge mode (doc-QA)")
        t.add_column("id"); t.add_column("correct"); t.add_column("retrieval"); t.add_column("cited")
        for r in report["docqa"]["rows"]:
            t.add_row(r["id"], f'{r["correct"]}', f'{r["retrieval_hit"]}', f'{r["cited"]}')
        console.print(t)
        console.print(f"[bold]doc-QA[/] correct={agg['correct']:.0%}  "
                      f"retrieval_hit={agg['retrieval_hit']:.0%}  cited={agg['cited']:.0%}")

    if "code" in report:
        agg = report["code"]["aggregate"]
        t = Table(title="Build mode (code)")
        t.add_column("id"); t.add_column("solved"); t.add_column("steps"); t.add_column("tool_errs")
        for r in report["code"]["rows"]:
            t.add_row(r["id"], f'{r["solved"]}', f'{r["steps"]}', f'{r["tool_errors"]}')
        console.print(t)
        console.print(f"[bold]code[/] solved={agg['solved']:.0%}  "
                      f"avg_steps={agg['steps']:.1f}  avg_tool_errors={agg['tool_errors']:.1f}")

    console.print(f"[dim]Report: {path}[/]")


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
