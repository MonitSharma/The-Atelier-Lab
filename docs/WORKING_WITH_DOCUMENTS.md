# Working with documents in Atelier

This is the practical document workflow. Use it when you want Atelier to
understand a paper, research plan, notes file, or code folder.

## Important current limitation

Atelier currently ingests PDF, Markdown, plain text, and source-code files.
It does not ingest `.docx` directly. Convert a Word document to PDF or plain
text/Markdown first, then ingest the converted copy. Keep the original DOCX
unchanged as the source of record.

## QAtelier quickstart

The document currently on this Mac is:

```text
~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
```

Start in a normal terminal from the document's directory:

```bash
cd ~/Downloads
atelier
```

For a research plan, a text/Markdown conversion is usually sufficient for a
first pass. On macOS, create a working copy with the built-in converter:

```bash
textutil -convert txt \
  -output QAtelier_Quantum_Adapters_Research_Plan.txt \
  QAtelier_Quantum_Adapters_Research_Plan.docx
```

Then leave the Atelier prompt or open a fresh one and index the converted copy:

```text
atelier › ingest ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.txt
atelier › sources
```

If the document contains important tables, figures, or layout-dependent
equations, export a PDF from Word/LibreOffice and use the PDF workflow instead:

```text
atelier › paper ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.pdf --ingest
atelier › paper-visual ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.pdf --json
```

## Ask questions in stages

Begin with retrieval and a broad map, then narrow the questions:

```text
atelier › search "What is the central research question and proposed contribution?"
atelier › ask --show-context "Summarize the document's objective, hypothesis, method, and expected result."
atelier › ask "List the required datasets, baselines, metrics, and implementation steps."
atelier › ask "Separate verified facts, assumptions, open questions, and risks."
atelier › ask "What should I implement or test first, and what evidence would make the project convincing?"
```

Use `--show-context` when checking an answer. The answer should cite the
converted source. If the document is not listed by `sources`, it has not been
indexed and Atelier cannot ground its answer in it.

## A disciplined research sequence

1. Preserve the original DOCX and record the conversion used.
2. Ingest exactly one working copy first.
3. Run `sources` and one `search` query to verify indexing.
4. Ask for structure: question, claims, method, data, baselines, metrics,
   risks, and deliverables.
5. Ask targeted questions about the sections you will actually implement.
6. Only then attach the relevant code repository with `cd` or `--workspace`.
7. Ask build mode to inspect the repository and propose a small, testable first
   experiment; do not ask it to implement the entire research plan at once.

## Privacy and state

Ingestion creates local runtime data under `~/Atelier`; it does not modify the
original document. `LOCAL_ONLY` is the default privacy policy. Use
[`ATELIER_OPERATOR_GUIDE.md`](ATELIER_OPERATOR_GUIDE.md) for workspace,
memory, `serve`, MCP, and model details.
