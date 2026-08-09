# Atelier release status

The current `master` line contains the deterministic foundation and acceptance
smoke through the initial v1.0 baseline. It has not yet completed the full
roadmap through Step 26. Incremental foundation tags include:

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
- `atelier-v1.0-acceptance`

Run the final deterministic check from `atelier_agent/`:

```bash
../.venv/bin/python -m atelier.cli acceptance
../.venv/bin/python -m pytest -q
../.venv/bin/python -m atelier.cli package check
```

The acceptance command deliberately avoids model inference, network calls,
external handoff, and destructive operations. It is a deterministic foundation
smoke, not full Step 26 release evidence. Qiskit simulation, solver-backed
optimization, durable workflow execution, expanded reliability/performance
evaluation, signed artifacts, and a richer Finder bundle remain explicit
roadmap work rather than hidden release claims.
