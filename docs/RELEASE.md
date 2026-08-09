# Atelier release status

The current `master` line has completed the deterministic implementation
roadmap through Step 26 and is tagged with incremental milestones:

- `atelier-core-v1.0`
- `atelier-workspace-v1.0`
- `atelier-repository-v1.0`
- `atelier-coder-v1.0`
- `atelier-build-v1.0`
- `atelier-routing-v1.0`
- `atelier-artifacts-v1.0`
- `atelier-research-v1.0`
- `atelier-security-v1.0`
- `atelier-runtime-v1.0`
- `atelier-ui-v1.0`
- `atelier-handoffs-v1.0`
- `atelier-release-foundations-v1.0`

Run the final deterministic check from `atelier_agent/`:

```bash
../.venv/bin/python -m atelier.cli acceptance
../.venv/bin/python -m pytest -q
../.venv/bin/python -m atelier.cli package check
```

The acceptance command deliberately avoids model inference, network calls,
external handoff, and destructive operations. Optional Qiskit simulation,
full hardware performance collection, signed artifacts, and a richer Finder
bundle remain explicit future extensions rather than hidden release claims.
