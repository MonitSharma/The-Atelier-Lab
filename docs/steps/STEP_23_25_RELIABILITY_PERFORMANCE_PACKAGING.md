# Steps 23–25 — Reliability, performance, and packaging foundations

Status: implemented on the current feature branch; merge and CI are the
release gate.

`atelier reliability --input TRIALS.json` summarizes trial rows with success
rate, Wilson 95% confidence intervals, category breakdowns, and a failure
taxonomy. `atelier performance` records elapsed milliseconds for shared local
service health, workflow-catalog, and library operations. `atelier package
check` validates required package files and Python syntax without mutating the
checkout.

These commands establish shared measurement and release gates for the frozen
repository, paper, data, research-verification, injection, memory, quantum,
optimization, and end-to-end suites. Full hardware performance collectors,
signed artifacts, and schema-repair automation remain final hardening work.
