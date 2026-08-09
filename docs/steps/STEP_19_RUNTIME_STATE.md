# Step 19 — Externalized runtime state

Status: implemented on the current feature branch; merge and CI are the
release gate.

Atelier now has a versioned runtime-home layout independent of the source
checkout:

```text
~/.atelier/
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
migrate` copies state into a `library/legacy_import` area and records every
created file. `atelier state rollback RECORD` removes only those copied files;
the original source remains intact.

The current checkout is not silently migrated. Activation of an external home
for all runtime paths is a later packaging/configuration step, after the
explicit migration plan has been reviewed.

Tests cover layout creation/validation, byte-counted migration planning,
copying, source preservation, and record-scoped rollback.
