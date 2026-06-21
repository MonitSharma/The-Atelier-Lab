"""The evaluation & reliability harness — the spine of the project (PROJECT.md §9).

Two frozen, version-controlled task suites and a runner that scores both modes:

    tasks_docqa/   knowledge mode: questions over the corpus with graded answers
    tasks_code/    build mode: a repo + a bug + a hidden test (the verifier)

The harness reports task success rate, steps-to-success, tool-error rate, and —
for knowledge mode — retrieval hit rate and groundedness. Every run is saved as
a JSON report so changes can be compared and regressions caught.
"""
