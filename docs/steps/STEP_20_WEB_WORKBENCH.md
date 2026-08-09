# Step 20 — Local web workbench

Status: **complete on the current development line**

`atelier serve` now exposes a dependency-free dashboard at:

```text
http://127.0.0.1:8787/ui
```

The page is intentionally a replaceable shell over `AtelierService`, not a
second application backend. It shows workspace/privacy state, model lifecycle
status, indexed library sources, workflow definitions, recent task traces, and
pending workflow approvals with approve buttons. It also provides forms for
capability routing, local-library search, source viewing, bounded upload, paper
actions, and repository actions.

The server remains loopback-only by default. It does not silently watch Finder,
index new files, or expose network research; those remain explicit operations
under the workspace policy.

The UI is covered by a smoke test that verifies the core panels, API calls, and
workflow approval endpoint.
