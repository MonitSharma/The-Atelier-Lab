# Step 20 — Local web workbench

Status: implemented on the current feature branch; merge and CI are the
release gate.

`atelier serve` now exposes a dependency-free dashboard at:

```text
http://127.0.0.1:8787/ui
```

The page is intentionally a replaceable shell over `AtelierService`, not a
second application backend. It shows workspace/privacy state, model lifecycle
status, indexed library sources, workflow definitions, recent task traces, and
the current approvals placeholder. It also provides forms for capability
routing and local-library search.

The server remains loopback-only by default. It does not silently watch Finder,
index new files, or expose network research; those remain explicit operations
under the workspace policy.

The UI is covered by a smoke test that verifies the core panels and API calls.
