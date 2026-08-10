# Steps 17–18 — Security boundary and backend service/API

Status: **complete on the current development line**

## Step 17 — Trust boundary

Tool calls made through `ToolRegistry` now pass through `SecurityBoundary`:

- shell commands use a small executable allowlist and reject shell operators,
  redirections, destructive executables, and destructive Git subcommands;
- existing workspace read/write/execute/network capabilities remain mandatory;
- networked tools still require `CLOUD_ALLOWED` plus explicit `network`;
- every registry call appends a minimal JSONL audit event without recording
  argument or output values;
- returned tool data is marked `untrusted_tool_output` and secret-looking
  strings (`token`, API keys, passwords, bearer values, and similar) are
  redacted before the model receives them;
- the shell remains opt-in, and `code_exec` retains its timeout and macOS
  network-sandbox behavior;
- destructive operations require a persisted, exact-match, one-use human
  confirmation token, and confirmation requests are exposed through the
  service/API and CLI.

The boundary is intentionally conservative. A command that needs a broader
capability is denied with a structured result rather than silently expanding
permissions. The web workbench exposes workflow approval actions; raw shell
approval remains explicit and never becomes an implicit model privilege.

## Step 18 — Shared application service

`atelier.service.AtelierService` is a JSON-friendly facade over the workspace
manager, tool registry, router, workflows, model lifecycle, library, search,
memory, artifacts, repository inspection, and task traces. It is independent
of Typer and can therefore be called by both CLI and UI code.

`atelier.api` supplies a localhost-only standard-library HTTP server:

```bash
atelier serve                    # http://127.0.0.1:8787
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/workflows
curl -X POST http://127.0.0.1:8787/route \
  -H 'Content-Type: application/json' \
  -d '{"task":"inspect this repository"}'
```

The server is bound to loopback by default. The service contract is the stable
foundation for the web workbench in Step 20; authentication, external binding,
and a hardened long-running daemon remain future hardening work.

## Verification

Tests cover shell injection/destructive-command rejection, secret redaction,
untrusted-output markers, audit privacy, shared service dispatch, and unknown
operation handling, in addition to the complete existing suite.
