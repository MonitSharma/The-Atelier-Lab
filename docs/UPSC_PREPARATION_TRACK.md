# UPSC preparation track

Atelier is a general local workbench, not a coding-only assistant. This track
adds the `exam_website` repository to the knowledge side of the system and
gives study questions an explicit routing policy.

## What is in `exam_website`

The repository at `~/code_projects/exam_website` is a static UPSC CSE practice
platform and a personal study archive. Its material includes:

- daily current affairs, PIB notes, reading-comprehension drills, and daily questions;
- weekly editorials, Sunday sweeps, sectional revision, CSAT, Physics optional, and quizzes;
- monthly checkpoints, GS mocks, and current-affairs compilations;
- UPSC Prelims PYQs, answer keys, generated question banks, and mock sets;
- ethics cases, essay topics, schemes/reports, places in news, and a fodder bank;
- Anki flashcards and analysis data;
- two Physics optional paper DOCX files;
- the Pariksha dashboard and its data-generation scripts.

The repository is about 128 MB including build output, dependencies, and
generated assets. Atelier should index the study material and question banks,
but not `node_modules`, `dist`, `vendor`, `.git`, or editor/worktree metadata.
Those are implementation artifacts and add noise without improving study
answers.

## First-time setup

Approve the repository as a read-only local study workspace:

```bash
atelier workspace add ~/code_projects/exam_website \
  --name upsc-prep \
  --capabilities read
```

Index the study material. The explicit paths include the repository's `data`
subfolders because the generic ingest walker intentionally skips directories
named `data` in software repositories:

```bash
atelier ingest \
  ~/code_projects/exam_website/README.md \
  ~/code_projects/exam_website/CSAT_Strategy_Guide.md \
  ~/code_projects/exam_website/daily \
  ~/code_projects/exam_website/weekly \
  ~/code_projects/exam_website/monthly \
  ~/code_projects/exam_website/reference \
  ~/code_projects/exam_website/reviews \
  ~/code_projects/exam_website/anki \
  ~/code_projects/exam_website/generated_questions \
  ~/code_projects/exam_website/generated_data \
  ~/code_projects/exam_website/data/raw \
  ~/code_projects/exam_website/data/processed \
  ~/code_projects/exam_website/data/answer_keys \
  ~/code_projects/exam_website/data/pyq_analysis.json \
  ~/code_projects/exam_website/Essay_Topic_2026-08-10.md \
  ~/code_projects/exam_website/Ethics_Case_2026-08-10.md
```

Preview the plan first with `--dry-run` if desired. Re-running the command is
incremental; unchanged files are skipped. Use `--sync` only when you want the
index to remove sources deleted below the supplied roots.

## How to use it for study

Use `search` to inspect evidence before asking for synthesis:

```bash
atelier search "Finance Commission 16th current affairs"
atelier search "UPSC mains answer structure climate adaptation"
atelier search "Physics optional PYQ semiconductor"
```

Use `ask` for grounded study help:

```bash
atelier ask --show-context \
  "Make a 10-question Prelims revision quiz on the indexed material about wetlands."

atelier ask --show-context \
  "Write a UPSC Mains GS-II answer on cooperative federalism using only the indexed notes. Include a thesis, arguments, examples, counterpoint, and way forward."

atelier ask \
  "Create a seven-day revision plan from my weak topics, separating Prelims facts, Mains answer writing, CSAT, and Physics optional."
```

For an individual source, use its path in the question or search result. The
answer should preserve source filenames and dates where available. For current
affairs, always ask Atelier to distinguish the note's publication date from
the date of the event and to flag claims that require external verification.

## Study workflows

### Prelims

Ask for retrieval-first revision, MCQs, elimination drills, answer-key
checking, and spaced-repetition cards. A good prompt names the subject,
date-range, difficulty, and whether the answer must be restricted to your
indexed notes.

```bash
atelier ask --show-context \
  "Give me 15 difficult Prelims MCQs on environment from June–August 2026 notes. After each answer, cite the source file and explain why the distractors are wrong."
```

### Mains

Ask for answer architecture, not just a polished answer. Atelier should
separate facts, examples, arguments, limitations, counterarguments, and the
way forward. Then ask it to critique your own draft rather than silently
rewriting it.

```bash
atelier ask --show-context \
  "Critique this GS-III answer against UPSC expectations: identify missing dimensions, unsupported claims, weak examples, and a better structure. Draft: ..."
```

### Essay and Ethics

Use the essay topics, fodder bank, and ethics cases to generate outlines,
counterarguments, examples, introductions, conclusions, and case-study
decision frameworks. Ask for multiple perspectives and explicitly label
illustrative examples so they are not mistaken for sourced facts.

### CSAT

Use the question bank for timed sets, error classification, and targeted drills.
For arithmetic or reasoning, Atelier should use deterministic calculation where
possible and show the intermediate steps.

### Physics optional

Use the two indexed DOCX papers and Physics notes for topic mapping, PYQ
classification, derivation practice, and answer checking. Ask it to flag when
an equation or derivation is uncertain instead of filling the gap from memory.

## Routing policy

Study questions are detected as the `study` capability domain. Short recall and
retrieval questions use the LFM worker. Mains answer writing, essays,
comparison, evaluation, and study planning use the temporary Qwen3-8B brain.
The future Qwen3.8-27B model will be evaluated on these tasks before it is
allowed to replace the brain.

The study route does not bypass evidence controls. It uses the same local
retrieval, citations, workspace permissions, and memory boundaries as research
questions. It should never present an AI-generated explanation as an official
UPSC answer key or as current fact without a source.

## Recommended evaluation set

Before trusting the study assistant, create a small frozen set covering:

1. Prelims fact retrieval with source/date citation;
2. difficult MCQ generation with answer-key consistency;
3. GS-II and GS-III Mains structure and evidence selection;
4. essay outline, counterargument, and conclusion quality;
5. ethics case reasoning with competing values;
6. CSAT calculations and intermediate-step correctness;
7. Physics optional derivations and PYQ topic mapping;
8. revision-plan usefulness and avoidance of unsupported claims.

Run the same set with Qwen3-8B and the released Qwen3.8-27B candidate. Record
answer quality, citation accuracy, latency, peak memory, and failure modes.
Promote the larger model only if the measured improvement is worth its memory
and speed cost on the 36 GiB M3 Pro.
