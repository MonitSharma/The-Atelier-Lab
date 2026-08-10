# Step 08 — Build Agent v2

Status: **complete**

## Delivered

`atelier_agent/agent/coding_workflow.py` adds a typed workflow boundary around
the existing ReAct loop. The model remains responsible for choosing tools and
making edits; deterministic code owns the evidence and acceptance decision.

```text
inspect → plan → identify files → baseline tests → edit
       → targeted tests → regression tests → diff review → certificate
```

The workflow is available through:

```bash
atelier code-fix "Fix the failing parser tests" --path /path/to/repository
```

## Acceptance rules

A certificate is accepted only when:

- the agent finishes within its step budget;
- an identification tool, edit tool, and test runner are observed;
- the independent final test run passes cleanly; and
- `git diff --check` reports no whitespace errors.

The model's final prose is not used as proof.

## Checkpoints and escalation

Each attempt snapshots bounded repository files before editing. Opt-in rollback
restores clean baseline files and removes workflow-created files; paths that
were already dirty when the workflow began are preserved. If the coder does
not produce an accepted certificate, the workflow can restore a clean baseline
and retry once with the `brain` role. A dirty worktree prevents automatic
replacement of the user's pre-existing changes.

Use `--rollback-on-failure` when the caller wants failed workflow edits removed.
The default preserves failed edits for inspection, which is safer for debugging.

## Verification

The unit tests cover checkpoint restoration, tool evidence extraction, and an
accepted certificate with a deterministic fake agent. The full repository suite
passes after this milestone. Larger repositories, repeated trials, and host
memory sampling remain part of Steps 23–24.
