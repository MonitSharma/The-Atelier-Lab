# IBM execution policy

IBM credentials are detected only as booleans. The preflight layer must capture
backend and compiled-resource metadata without submitting a job. Physical
execution is a later validation stage after the selected candidate panel,
parameters, compressor, samples, observables, shots, and compilation policy
are frozen.

`preflight.py` provides the safe credential-presence check, read-only backend
snapshots, and a non-bypassable frozen-panel gate. It does not expose token
values and has no job-submission function.
