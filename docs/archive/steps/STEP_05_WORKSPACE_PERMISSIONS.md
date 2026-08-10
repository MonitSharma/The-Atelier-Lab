# Step 05 — Workspace and Permission Architecture

Status: **complete on the current development line**

## Objective

Replace the process-current-directory assumption with explicit, persisted,
capability-scoped workspace roots. Atelier can now attach multiple approved
directories while keeping relative paths anchored to one active workspace.

## CLI

```bash
atelier workspace add PATH [--name NAME] \
  [--capabilities read,write,execute] [--privacy LOCAL_ONLY]
atelier workspace open NAME
atelier workspace list
atelier workspace close NAME
```

The registry is stored in the external runtime at
`~/Atelier/workspaces/registry.json` by default (or under `ATELIER_HOME`) and
is ignored by Git. The source checkout is preserved as a system workspace for
development; new user-added roots default to read-only and `LOCAL_ONLY`.

## Permission model

Each approved root has `read`, `write`, `execute`, and optional `network`
capabilities. `LOCAL_ONLY` is the default and rejects network-capability grants.
Shell commands with common network markers are rejected unless the active
workspace has both network capability and `CLOUD_ALLOWED`. Python snippets
remain network-blocked by the macOS seatbelt when the platform provides it;
without that enforcement, a local-only context refuses execution.

## Path safety

Every context-aware tool resolves relative paths against the active workspace,
canonicalizes symlinks, finds the most-specific approved root, checks the
requested capability, and rejects paths outside every attached root. This
prevents `..` and symlink escapes while allowing absolute paths inside another
attached root for multi-workspace tasks.

The old `PROJECT_ROOT` resolver remains only as a compatibility fallback for
direct unit-level calls. Agent, MCP, and CLI registries receive an explicit
immutable `WorkspaceContext`.

## Verification

Tests cover multiple attached roots, relative escapes, symlink escapes,
read-only writes, `LOCAL_ONLY` network rejection, and invalid network grants.

```text
103 passed, 1 warning
repository checks: PASS
compileall: PASS
```

This is an application-level capability boundary, not a kernel sandbox. Step 17
adds stronger command allowlists, secret redaction, prompt-injection
protection, one-use confirmations, audit logs, and hardened execution policy;
OS-level isolation remains an explicit future hardening extension.
