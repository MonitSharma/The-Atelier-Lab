# Step 26 — Deterministic acceptance and release

`atelier acceptance` runs an offline acceptance smoke across package readiness,
service/workspace state, workflows, QASM and optimization tools, security
policy, network denial, web UI, registry dispatch, Finder planning, handoff
creation, project memory, and runtime recovery. It reports every check instead
of stopping at the first failure.

The release checklist also runs the full pytest suite and `atelier package
check`. Model-backed paper ingestion/answering, optional Qiskit capabilities,
hardware performance collectors, and real external handoff remain explicitly
operator-controlled; the release does not pretend to have verified them with
the local offline smoke.
