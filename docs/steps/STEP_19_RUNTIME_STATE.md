# Step 19 — Externalized runtime state

Status: **complete on the current development line**

Atelier now has a versioned runtime-home layout independent of the source
checkout:

```text
~/Atelier/
├── library/       papers, extracted artifacts, and imported legacy state
├── databases/     manifests and indexes
├── workspaces/    workspace registry/state
├── config/        generated configuration
├── cache/         rebuildable caches
├── logs/          operational logs
└── backups/       recovery material
```

The location is controlled by `ATELIER_HOME` or `--home`. `atelier init`
creates the layout and a versioned manifest. `atelier state validate` checks
it without changing anything. `atelier state plan` reports the files and bytes
that would be imported from the current repository data. `atelier state
migrate` copies legacy repository state into the mapped runtime layout and
records every created file. `atelier state rollback RECORD` removes only those
copied files; the original source remains intact. The active Mac runtime is
already externalized and its three-paper retrieval index has been validated at
223 chunks.

The current checkout remains independently disposable; runtime paths are
derived from the external home unless explicitly overridden for a test.

Tests cover layout creation/validation, byte-counted migration planning,
copying, source preservation, and record-scoped rollback.
