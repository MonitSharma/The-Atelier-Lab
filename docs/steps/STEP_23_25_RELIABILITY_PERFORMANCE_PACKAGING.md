# Steps 23–25 — Reliability, performance, and packaging foundations

Status: **complete on the current development line**

`atelier reliability --input TRIALS.json` summarizes trial rows with success
rate, Wilson 95% confidence intervals, category breakdowns, and a failure
taxonomy. `atelier reliability --suite v2 --repetitions 2` currently passes
22/22 frozen cross-component trials across routing, repository, workflow,
data, visual, memory, security, research, quantum, and optimization cases.
`atelier performance` records elapsed milliseconds plus platform, free-disk,
and peak-process-memory snapshots for shared local service operations.
`atelier package check` validates required package files and Python syntax;
`atelier state repair` and package export/restore provide recovery paths.

These commands establish shared measurement and release gates for the frozen
repository, paper, data, research-verification, injection, memory, quantum,
optimization, visual, and end-to-end suites. Full host-level unified-memory and
concurrency collectors, signed artifacts, and schema migration automation
remain final hardening work.
