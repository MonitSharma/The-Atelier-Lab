# Atelier release status

The current development line contains the deterministic foundation and the
verified local v1.0 acceptance scenario. Incremental foundation tags include:

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

Run the release checks from `atelier_agent/`:

```bash
../.venv/bin/python -m atelier.cli acceptance
../.venv/bin/python -m atelier.cli acceptance --clean
../.venv/bin/python -m pytest -q
../.venv/bin/python -m atelier.cli package check
../.venv/bin/python -m atelier.cli reliability --suite v2 --repetitions 3
../.venv/bin/python -m atelier.cli performance
```

The clean acceptance commands deliberately avoid network calls, external
handoff, and destructive operations. The release evidence additionally includes
isolated local Qwen3-8B paper retrieval and repository-edit runs. Qiskit
provider execution/backend comparison, external solver integrations, hardened
OS isolation, signed artifacts, automatic cloud routing, and live frontier
handoffs remain explicit extensions rather than hidden claims.
