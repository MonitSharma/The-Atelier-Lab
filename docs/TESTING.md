# Testing Atelier — exercising every ability

This is a hands-on playbook for verifying each capability of your agent, from
the environment up to a full autonomous coding task. Every command is copy-paste
ready. Run from the repo root with the venv active:

```bash
source .venv/bin/activate
```

> Tip: set `ATELIER_NO_BANNER=1` to hide the magician banner in scripted runs.

There are two kinds of testing here:
1. **Automated tests** (`pytest`) — fast, deterministic, no model. Run these constantly.
2. **Live ability checks** — you drive the real local model and watch it work.

---

## 0. Prerequisites & health

```bash
ollama serve &                 # if not already running
atelier doctor
```

**Expect:** a table with `model:brain/worker/heavy` all green, the vector store
reachable, and the embed model listed. If a model is red, run the `ollama pull`
it prints.

---

## 1. Automated test suite (run this first, always)

```bash
pytest -q
```

**Expect:** all green. These cover the calculator sandbox, file
read/write/edit + AST edit + path-escape rejection, markdown chunking, the ChromaDB
round-trip, every build-mode tool, and the ReAct engine (with a scripted brain).
None of them call Ollama, so they finish in seconds.

Useful slices:

```bash
pytest tests/test_react.py -q          # the agent loop logic
pytest tests/test_tools_build.py -q    # build-mode tools
pytest -k "calculator or store" -q     # filter by name
```

---

## 2. Knowledge mode — "talk to my notes"

### 2a. Ingest
```bash
atelier ingest ./Project.md ./myNotes.md          # or point at ~/YourNotes
atelier sources                                    # confirm what's indexed
```
**Expect:** an "Ingest complete" panel (files indexed, chunks stored, vector
dim 768). `sources` lists the files.

### 2b. Grounded answer (the core ability)
```bash
atelier ask "What are the hard constraints of this project, and what is the binding limit?"
```
**Expect:** an answer that quotes your notes with citations like `[1] [2]`, plus
a `Sources:` line. The "binding limit" wording should match `Project.md`
verbatim — that proves it's grounded, not hallucinated.

### 2c. Prove retrieval is doing the work (before/after)
Ask something only answerable from your notes vs. the model's own knowledge:
```bash
# WITH your notes (retrieval on — the normal path):
atelier ask "Which embedding model did I choose and why?"

# WITHOUT retrieval (baseline — ask the raw model the same thing):
ATELIER_NO_BANNER=1 python - <<'PY'
from agent.brain import chat
print(chat([{"role":"user","content":"Which embedding model did Monit choose for Atelier and why?"}], role="brain"))
PY
```
**Expect:** the first answers correctly (`BAAI/bge-base-en-v1.5`, with the
reason); the baseline either refuses or guesses. That gap *is* the value of RAG.

### 2d. Inspect what was retrieved
```bash
atelier ask -k 8 --show-context "what is build mode's verifier?"
```
**Expect:** a "Retrieved context" panel with the actual passages, so you can
judge retrieval quality yourself.

### 2e. Interactive
```bash
atelier chat          # ask follow-ups; 'exit' to quit
```

---

## 3. Build-mode tools (test each in isolation, no model)

Each tool is a plain function returning a status dict — you can call them directly.

```bash
ATELIER_NO_BANNER=1 python - <<'PY'
from tools.repo_map import run_repo_map
from tools.search import run_search
from tools.code_exec import run_python
from tools.test_runner import run_tests

print("repo_map:", run_repo_map({"path": "rag"})["file_count"], "files")
print("search:", len(run_search({"pattern":"def retrieve","path":"rag"})["hits"]), "hits")
print("code_exec:", run_python({"code":"print(2**10)"})["stdout"].strip(),
      "| network blocked:", run_python({"code":"pass"})["network_blocked"])
print("test_runner:", run_tests({"path":"tests","k":"calculator"})["counts"])
PY
```
**Expect:** repo_map reports the files in `rag/`; search finds `retrieve`;
code_exec prints `1024` and `network blocked: True` (macOS seatbelt active);
test_runner returns `passed` counts for the calculator tests.

### Verify the sandbox really blocks the network
```bash
ATELIER_NO_BANNER=1 python - <<'PY'
from tools.code_exec import run_python
r = run_python({"code": "import urllib.request as u; u.urlopen('http://example.com', timeout=3); print('REACHED NET')"})
print("status:", r["status"], "| net_blocked:", r["network_blocked"])
print(r["stderr"][-200:])
PY
```
**Expect:** `status: error` and the snippet failing to reach the network (an
operation-not-permitted / connection error) — model-written code cannot phone
home. (If `sandbox-exec` is unavailable, `net_blocked` is `False`; the doc is
honest that this is best-effort.)

### Verify file tools can't escape the workspace
```bash
ATELIER_NO_BANNER=1 python - <<'PY'
from tools.files import run_read_file, run_write_file
print(run_read_file({"path": "/etc/passwd"})["error_type"])        # path_not_allowed
print(run_write_file({"path": "../escape.txt", "content": "x"})["error_type"])  # path_not_allowed
PY
```
**Expect:** both print `path_not_allowed`.

---

## 4. The agent loop — autonomous, dual-mode (the headline ability)

### 4a. Build mode: fix a failing test, proven green
Re-introduce the classic bug into the sample task, then turn the agent loose:
```bash
# break it
python - <<'PY'
from pathlib import Path
p = Path("sample_task/mathutils.py")
p.write_text(p.read_text().replace("return a + b", "return a - b  # BUG"))
PY
pytest sample_task/ -q          # confirm it FAILS

# fix it autonomously
atelier agent "A test in sample_task/ is failing. Use repo_map and read_file to \
understand it, fix the bug with edit_file, then run test_runner on sample_task \
to prove all tests pass. Only finish when tests pass cleanly." --max-steps 12

pytest sample_task/ -q          # confirm it now PASSES
```
**Expect:** a streamed trace — `repo_map → read_file → read_file → edit_file →
test_runner → final` — finishing in well under 10 steps, and the independent
`pytest` going green. Open the printed `Trace:` JSON to see every step.

### 4b. Knowledge mode through the agent (not just the CLI path)
```bash
atelier agent "Using search_notes, tell me what my project's non-goals are, and \
list them as bullet points."
```
**Expect:** the agent calls `search_notes`, then answers from your notes. This is
knowledge mode as an *agent capability*.

### 4c. Combined knowledge → build (the end goal, PROJECT.md §2)
```bash
atelier agent "Look up in my notes (search_notes) what the calculator tool is \
supposed to support, then write a new test file sample_task/test_extra.py that \
checks 2**5 == 32 using code_exec to confirm the expected value first, and run it."
```
**Expect:** the agent retrieves context, uses `code_exec` to confirm `2**5`,
writes a test with `write_file`, and runs `test_runner`. This composes both modes
in one task.

### 4d. Pick the model size
```bash
atelier agent "..."          # qwen3:14b (brain) — default
atelier agent "..." --heavy  # gemma4:26b — harder reasoning, slower
```

---

## 5. Reflection / error recovery (reliability)

The agent is supposed to recover from its own mistakes rather than crash. The
scripted tests pin this:
```bash
pytest tests/test_react.py -q -k "reflect or unknown_tool"
```
**Expect:** `test_reflects_on_bad_json_then_recovers` (bad model output → fed
back → recovers) and `test_unknown_tool_is_observed_not_crashed` both pass.

To watch it live, give the agent a task where a tool will error (e.g. ask it to
edit a non-unique string) and observe it adjust on the next step.

---

## 6. Observability — every run leaves a trace

```bash
ls -t data/traces | head        # newest runs
python -m json.tool data/traces/$(ls -t data/traces | head -1)
```
**Expect:** a JSON file per agent run containing the goal and every step (raw
model output, parsed decision, tool, observation, latency). This is the raw
material for the eval harness (next milestone) and for debugging failures.

---

## 5b. Memory — it remembers across sessions

```bash
pytest tests/test_memory.py -q              # incl. a cross-'session' persistence test
atelier remember "I prefer Apache-2.0 and pytest" --tags prefs
atelier recall "what license does the user want?"
atelier memory                              # list all stored facts
```
**Expect:** `recall` returns the stored fact ranked by a similarity score, even
though the query wording differs. Prove persistence across processes:
```bash
python -c "from agent.memory import get_memory; get_memory().remember('the brain model is qwen3:14b')"
python -c "from agent.memory import get_memory; print(get_memory().recall('which model reasons?')[0].text)"
```
**Expect:** the second (separate) process recalls what the first stored.

## 5c. Hybrid retrieval + reranking

```bash
pytest tests/test_retrieval.py -q           # BM25 + RRF fusion logic (no model)

# Dense-only vs hybrid vs reranked — compare what comes back:
ATELIER_USE_HYBRID=0 atelier ask --show-context "exact term only in one note"
atelier ask --show-context "exact term only in one note"           # hybrid (default)
ATELIER_RERANK=1   atelier ask --show-context "exact term only in one note"
```
**Expect:** hybrid surfaces chunks containing rare exact terms that dense-only
can miss; reranking reorders the top results by a sharper relevance score
(downloads a small model the first time).

## 5d. MCP server — use the tools from another client

```bash
# Full client↔server handshake over stdio (no external client needed):
ATELIER_NO_BANNER=1 python - <<'PY'
import asyncio, sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m","atelier.mcp_server"])
    async with stdio_client(p) as (r,w):
        async with ClientSession(r,w) as s:
            await s.initialize()
            print("tools:", [t.name for t in (await s.list_tools()).tools])
            print((await s.call_tool("calculator", {"expression":"6*7"})).content[0].text)
asyncio.run(main())
PY
```
**Expect:** a list of 12 tools and `calculator(6*7)` returning `42`. To wire it
into Claude Desktop/Code, point an MCP server entry at the command `atelier mcp`.

## 6b. Reliability eval — measure, don't guess

This is what makes Atelier a *system* rather than a demo: frozen task suites with
scored outcomes you can track over time.

```bash
pytest tests/test_eval.py -q          # harness logic (fast, no model)
atelier eval --mode code              # build mode only (~1–2 min)
atelier eval --mode docqa             # knowledge mode only (~2–3 min)
atelier eval                          # both
atelier eval --judge                  # add the local LLM-as-judge for groundedness
```

**Expect:** two tables. Knowledge mode reports `correct / retrieval_hit / cited`
per question and overall percentages; build mode reports `solved / steps /
tool_errors` per task. A JSON report is saved to `data/eval_reports/` for
comparison after future changes.

**The suites are frozen on purpose** (`eval/tasks_docqa/`, `eval/tasks_code/`).
Don't edit them casually — changing the ruler invalidates comparisons. Add *new*
tasks instead. To prove the eval actually discriminates, break something and
watch the score drop:
```bash
# temporarily sabotage retrieval, re-run docqa, then revert
ATELIER_RETRIEVAL_K=1 atelier eval --mode docqa
```

### Regression gate
```bash
atelier eval --gate          # runs, then fails (exit 1) if any metric dropped
```
**Expect:** after a clean run it prints "no regressions vs. last report"; if a
change lowered `correct` / `retrieval_hit` / `solved`, it prints the deltas and
exits non-zero — wire this into a pre-commit or CI step. The gate logic itself is
unit-tested in `tests/test_eval.py`.

### Eval plots
```bash
atelier eval --mode all
atelier eval-plots
```
**Expect:** SVG charts under `data/eval_reports/plots/<report-name>/`, including
doc-QA overview, doc-QA by category, code overview, code by difficulty, code by
edit scope, and code steps by task. Plot generation itself is unit-tested in
`tests/test_eval_plots.py` with a fake report, so it does not require Ollama.

### Combined eval
```bash
atelier eval --mode combined
```
**Expect:** each task first uses `search_notes`, then edits a small repo and
proves the result with `test_runner`. A row only counts as solved if both the
tests pass and the trace contains `search_notes`.

### Planner-router data
```bash
make planner-data
```
**Expect:** JSONL files under `models/router/data/` that map task prompts to
`category`, `difficulty`, `edit_scope`, `tool_plan`, and `model_route`.

## 7. One-command sanity sweep

```bash
atelier doctor && pytest -q && echo "ATELIER OK"
```
Run this after any change. If it ends in `ATELIER OK`, the foundation,
knowledge mode, and build-mode tooling are all intact.

---

## What "passing" looks like, summarized

| Ability | Command | Success signal |
|---|---|---|
| Health | `atelier doctor` | all models green |
| Unit tests | `pytest -q` | all fast tests passed |
| Ingest | `atelier ingest <path>` | chunks stored, dim 768 |
| Grounded Q&A | `atelier ask "..."` | cited answer matching your notes |
| RAG lift | §2c before/after | grounded wins over baseline |
| Sandbox | §3 network test | code can't reach the net |
| Workspace guard | §3 escape test | `path_not_allowed` |
| Autonomous fix | `atelier agent "fix sample_task"` | tests go green, trace shows test_runner |
| Recovery | `pytest tests/test_react.py` | reflection tests pass |
| Traces | `ls data/traces` | one JSON per run |
