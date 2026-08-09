# Atelier release status

The current development line contains the deterministic foundation and
acceptance smoke through the initial v1.0 baseline. It has not yet completed
the full roadmap through Step 26. Incremental foundation tags include:

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
../.venv/bin/python -m atelier.cli acceptance --clean
../.venv/bin/python -m pytest -q
../.venv/bin/python -m atelier.cli package check
../.venv/bin/python -m atelier.cli reliability --suite v2 --repetitions 3
../.venv/bin/python -m atelier.cli performance
```

The acceptance commands deliberately avoid model inference, network calls,
external handoff, and destructive operations. They are deterministic foundation
and clean-state evidence, not full Step 26 release evidence. Qiskit provider
transpilation/backend comparison, external solver integrations, hardened OS
isolation, signed artifacts, and live frontier handoffs remain explicit release
extensions rather than hidden claims.
