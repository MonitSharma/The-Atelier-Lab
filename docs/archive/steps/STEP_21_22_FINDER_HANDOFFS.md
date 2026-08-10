# Steps 21–22 — Finder actions and frontier handoffs

Status: implemented on the current feature branch; merge and CI are the
release gate.

## Finder actions

`atelier finder plan ACTION PATH` provides an opt-in bridge suitable for a
macOS Finder Quick Action or Shortcuts shell action. Supported actions are
`send_to_atelier`, `add_to_library`, `characterize_paper`, and `explain_file`.
The command resolves the path through the active workspace and returns the
next explicit Atelier operation. It does not install a watcher, index the Mac,
or mutate the library by itself.

## Handoff bundles

`atelier handoff create` writes a JSON or Markdown bundle containing the task,
selected context, evidence, constraints, requested output, target provider,
timestamp, and an explicit external-transfer approval flag. Supported targets
are Claude, Codex, and Gemini. Creating a bundle never sends it; the user can
review the file before any external action.

Both surfaces are covered by tests for workspace resolution, non-watching
behavior, local output, and the default-unapproved transfer state.
