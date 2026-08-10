# Working with documents in Atelier

This is the practical document workflow. Use it when you want Atelier to
understand a paper, research plan, notes file, image, archive, or code folder.

## Supported formats

| Format | Current behavior |
|---|---|
| PDF | Native page extraction, paper metadata, page-aware chunks, and OCR fallback for image-only pages |
| Markdown, text, HTML, RTF, TeX, JSON, CSV/TSV, notebooks, source code | Local text extraction and retrieval chunks |
| DOCX | Paragraph text and tables through the Office XML package |
| PPTX | Slide text through the Office XML package |
| XLSX/XLSM | Visible cell values through the workbook XML package |
| EPUB | HTML/XHTML chapter text |
| PNG, JPG, TIFF, WEBP, BMP | Local Tesseract OCR when installed; visual layout is not represented in text retrieval |
| ZIP | Safe, non-executing extraction of supported text members; archives are not unpacked to disk |

Old binary Office formats (`.doc`, `.ppt`, `.xls`), encrypted files, and
arbitrary binaries require conversion or a dedicated reader. Atelier does not
execute files, install software from archives, or send them to a cloud service.

## Format and accuracy limits

Atelier now reads modern `.docx` directly. For documents where layout,
equations, or embedded figures matter, PDF remains the preferred representation
because it retains page evidence. Keep the original DOCX unchanged as the
source of record and ingest a working copy or the PDF export.

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

For an image or handwritten scan, ingest it directly first. Atelier will use
local Tesseract OCR when available:

```text
atelier › ingest ~/Downloads/handwritten-note.png
atelier › ask "Transcribe the legible content and mark uncertain words."
```

OCR is an extraction aid, not a proof of handwriting accuracy. For diagrams,
chemical structures, equations, or spatial layout, use the original image/PDF
with a vision-capable workflow and verify the result manually.

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
