# Atelier user guide

Atelier is a local-first research and coding workbench. Its everyday workflow
is intentionally small:

```text
ingest → search/ask → agent or code-fix
```

`ingest` builds a local searchable library. `search` shows evidence without
asking a model to synthesize it. `ask` answers from that evidence. `agent` can
combine retrieval with repository tools, while `code-fix` is the more
constrained inspect → edit → test workflow.

The default privacy mode is local. Ollama serves models on the Mac, and the
indexed documents, vectors, traces, and memory live under `~/Atelier`.

For UPSC preparation using the `exam_website` study archive, see
[`UPSC_PREPARATION_TRACK.md`](UPSC_PREPARATION_TRACK.md).

## Start here

From any normal terminal:

```bash
atelier
```

Inside the interactive prompt, use ordinary terminal commands such as `cd`,
`pwd`, `ls`, `find`, `rg`, `git`, and `cat`. Tab completion works for Atelier
commands and filesystem paths. Type `help` for the short guide or `exit` to
leave.

Outside the prompt, the same commands work directly:

```bash
atelier guide
atelier doctor
```

The default `atelier --help` intentionally shows only the daily commands.
Advanced commands remain available; use `atelier advanced-help` when you need
them.

## The daily commands

| Command | What it does | Changes local state? |
|---|---|---:|
| `atelier ingest PATH...` | Extracts and embeds supported files/folders | Yes |
| `atelier sources` | Lists files currently indexed | No |
| `atelier search QUERY` | Retrieves passages without model synthesis | No |
| `atelier ask QUESTION` | Answers from retrieved local evidence | No |
| `atelier paper FILE.pdf` | Creates a cached Fast Paper characterization | Yes, cache only |
| `atelier agent TASK` | Runs the full research + repository agent | Possibly |
| `atelier code-fix TASK` | Runs the guarded coding workflow | Possibly |
| `atelier remember TEXT` | Stores a durable memory fact | Yes |
| `atelier recall QUERY` | Searches durable memory | No |
| `atelier doctor` | Checks models, index, memory, and workspaces | No |

### 1. Ingest material

Atelier supports PDF, DOCX, PPTX, XLSX/XLSM, EPUB, Markdown, text, code,
images, and ZIP archives. Modern DOCX files preserve headings, tables, and
embedded-image locations. PPTX files preserve slide numbers, speaker notes,
and slide-linked images. Images and image-only PDF pages use Tesseract when
available plus the local `gemma4:26b` vision model for handwriting, diagrams,
and equations.

```bash
atelier ingest ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
atelier sources
```

If a file was already indexed before an extraction upgrade, force regeneration:

```bash
atelier ingest --force ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx
```

Useful ingestion options:

```bash
atelier ingest PATH --dry-run   # inspect the plan; changes nothing
atelier ingest PATH --sync      # remove indexed files deleted below PATH
atelier ingest PATH --reset     # destructive: clear the selected local index first
```

Use `--reset` only when you deliberately want to rebuild the index. It does
not delete your original files.

### 2. Inspect evidence before asking

```bash
atelier search "parameter-matched classical baselines"
atelier search --source QAtelier_Quantum_Adapters_Research_Plan.docx \
  "falsifiers and hardware validation"
```

`search` is useful when you want to see exactly what retrieval found. Results
retain page, slide, heading, table, image, speaker-note, and archive-member
locations where available.

### 3. Ask grounded questions

```bash
atelier ask --show-context \
  "What is the central QAtelier question, its proposed contribution, and the evidence required before claiming quantum advantage?"
```

Use `--show-context` when checking an answer. Use `-k 8` when a question needs
more retrieved passages:

```bash
atelier ask -k 8 "Separate explicit assumptions from recommendations in the plan."
```

Use `--heavy` only for difficult synthesis. It uses the 26B local model and is
slower and more memory-intensive:

```bash
atelier ask --heavy "Compare the plan's hypotheses and proposed falsifiers."
```

### 4. Work with a repository

Start with a deterministic inspection:

```bash
cd ~/code_projects/The-Atelier-Lab
atelier repo inspect .
atelier repo status .
atelier repo tests .
```

For a small, controlled coding task:

```bash
atelier code-fix \
  "Add a regression test for the DOCX table citation and run the test suite." \
  --path ~/code_projects/The-Atelier-Lab
```

For a broader research-to-code task:

```bash
atelier agent \
  "Read the QAtelier plan, inspect this repository, and propose the smallest reproducible experiment. Do not edit files yet."
```

`code-fix` is preferred when you already know the code change. `agent` is
preferred when the task requires searching notes, inspecting a repository, or
using several tools. The agent does not receive the powerful shell tool unless
you explicitly pass `--shell`.

Atelier also has a study route. Questions mentioning UPSC, Prelims, Mains,
CSAT, current affairs, essays, ethics, or optional subjects are routed toward
the indexed preparation material. Short recall questions use the worker;
answer writing, comparison, evaluation, and study planning use the temporary
brain model.

For a repository outside the current directory, approve it explicitly:

```bash
atelier workspace add ~/code_projects/MyRepo \
  --name my-repo --capabilities read,write,execute
atelier workspace open my-repo
atelier code-fix "Run the tests and fix the failing parser." --path ~/code_projects/MyRepo
```

### 5. Remember project decisions

```bash
atelier remember "QAtelier remains a parallel research branch until hardware evidence is complete."
atelier recall "What is the integration rule for QAtelier?"
```

Use memory for durable decisions and preferences, not for storing entire
documents. Documents belong in the indexed library.

## Worked example: QAtelier from DOCX to experiment plan

```bash
# 1. Index the source and its tables/images.
atelier ingest --force ~/Downloads/QAtelier_Quantum_Adapters_Research_Plan.docx

# 2. Confirm the source is present.
atelier sources

# 3. Inspect direct evidence.
atelier search --source QAtelier_Quantum_Adapters_Research_Plan.docx \
  "shared compressor parameter matching hardware"

# 4. Ask for a grounded summary with visible evidence.
atelier ask --show-context \
  "Summarize the research question, assumptions, methods, risks, and falsifiers. Cite headings, tables, and embedded figures when relevant."

# 5. Ask a visual/equation question.
atelier ask --show-context \
  "Transcribe the important equations and describe each embedded diagram. Mark anything that needs human review."

# 6. Move to implementation only after reviewing the answer.
cd ~/code_projects/The-Atelier-Lab
atelier agent \
  "Using the reviewed QAtelier plan, inspect the repository and propose the first experiment as a small set of files and tests. Do not modify files."
```

The answer is not automatically scientific truth. OCR and vision are evidence
aids. Equation transcriptions, handwriting, diagrams, and low-confidence text
 must be checked before publication or hardware decisions.

## Models and routing

| Role | Current model | Purpose |
|---|---|---|
| Worker | LFM2.5 2.6B Q6 | cheap extraction, classification, structured subtasks |
| Brain | Qwen3 8B | normal local reasoning and agent planning |
| Coder | Qwen3 8B | repository edits and tests |
| Heavy | Gemma4 26B | difficult synthesis and long-context reasoning |
| Vision | Gemma4 26B | handwriting, diagrams, equations, embedded images |
| Embeddings | Qwen3-Embedding 4B | local semantic retrieval |

The 26B model is shared by heavy reasoning and vision. Atelier loads models on
demand through Ollama; avoid running several large operations concurrently on a
36 GiB Mac.

## Advanced commands: when and why

These are real capabilities, but they are intentionally hidden from the daily
help so the normal workflow stays readable.

| Area | Commands | Use when |
|---|---|---|
| Visual/research | `paper-visual`, `profile`, `research-lookup` | inspecting PDF quality, structured artifacts, or approved external evidence |
| Services | `serve` | exposing the localhost API to a web UI or integration |
| MCP | `mcp` | an external MCP client needs Atelier's tool bridge |
| Tools | `tools` | auditing the tools available to the agent |
| Evaluation | `eval`, `benchmark-coding`, `benchmark-retrieval`, `eval-plots` | measuring the system, not daily research |
| Science | `quantum`, `optimize` | deterministic circuit or optimization analysis |
| Runtime | `init`, `state`, `package` | setup, migration, backup, or release work |
| Durable workflows | `workflow`, `security` | checkpointed tasks and explicit destructive approvals |
| Integrations | `finder`, `handoff`, `research` | opt-in Finder actions, handoff bundles, or network-approved research |

### `serve` and `mcp` are not normal chat modes

`serve` runs a localhost HTTP API for the web UI and integrations. `mcp` runs a
long-lived Model Context Protocol bridge for an external MCP client. Neither is
needed to ask questions in the terminal.

Run them in a separate terminal when needed:

```bash
atelier serve
# or
atelier mcp
```

Pressing `Ctrl-C` stops that server/bridge process. It should not be used as a
way to cancel an individual research answer. Keep your normal `atelier` prompt
in another terminal; the interactive session catches cancellation of ordinary
subprocess commands and remains open.

## Troubleshooting

```bash
atelier doctor                 # first diagnostic
atelier models status --json   # detailed Ollama model state
atelier sources                # confirm indexing
atelier ingest PATH --dry-run # inspect what would change
```

If an answer is weak, use `atelier search ...` first, then repeat
`atelier ask --show-context ...` with a more specific question. If an image or equation is uncertain, trust the
`HUMAN REVIEW` flag and inspect the original file.
