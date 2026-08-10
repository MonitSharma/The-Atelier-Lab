# Working with documents in Atelier

This is the practical document workflow. Use it when you want Atelier to
understand a paper, research plan, notes file, image, archive, or code folder.

## Supported formats

| Format | Current behavior |
|---|---|
| PDF | Native page extraction, paper metadata, page-aware chunks, and OCR fallback for image-only pages |
| Markdown, text, HTML, RTF, TeX, JSON, CSV/TSV, notebooks, source code | Local text extraction and retrieval chunks |
| DOCX | Heading-aware paragraphs, tables, and embedded images through the Office XML package; local vision descriptions for images |
| PPTX | Slide text, speaker notes, and slide-linked embedded images through the Office XML package |
| XLSX/XLSM | Visible cell values through the workbook XML package |
| EPUB | HTML/XHTML chapter text |
| PNG, JPG, TIFF, WEBP, BMP | Local Tesseract OCR plus the installed Gemma 4 vision model for handwriting, diagrams, and equations |
| ZIP | Recursive, non-executing extraction of supported text/Office/image members with member citations and strict depth, count, size, path, encryption, and compression-ratio limits |

Old binary Office formats (`.doc`, `.ppt`, `.xls`), encrypted files, and
arbitrary binaries require conversion or a dedicated reader. Atelier does not
execute files, install software from archives, or send them to a cloud service.

## Format and accuracy limits

Atelier now reads modern `.docx` directly and records headings, tables, and
embedded-image locations. PDF remains useful when exact page layout matters.
Native extraction and OCR are evidence layers; vision descriptions and equation
transcriptions carry a confidence/review flag and should be checked by a human
before publication.

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

For a research plan, direct DOCX ingestion is sufficient for a text-first pass:

```text
atelier › ingest ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
atelier › sources
```

After an extraction upgrade, use `--force` once if the file was already in
the index so Atelier regenerates its headings, media descriptions, and review
metadata:

```text
atelier › ingest --force ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
```

If you want a plain-text working copy, macOS also provides a built-in converter:

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

For an image or handwritten scan, ingest it directly first. Atelier combines
local Tesseract OCR with the installed `gemma4:26b` vision model when available:

```text
atelier › ingest ~/Downloads/handwritten-note.png
atelier › ask "Transcribe the legible content and mark uncertain words."
```

OCR and vision are extraction aids, not proof of handwriting or equation
accuracy. `ocr_confidence`, `vision_confidence`, and `human_review` metadata are
preserved in retrieval context. Verify low-confidence text, diagrams, and
equations manually.

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
