# QAtelier hardware decisions

## 2026-08-10 — No hardware campaign authorized

Decision: do not submit IBM or Quantinuum jobs in the current phase.

Evidence available:

- S0 simulator calibration was negative for the short preregistered quantum
  training budget.
- S1 classical reference panels were archived across SST-2, MRPC, CoLA, SciFact,
  and controlled interaction order.
- The expanded S2 screen remained near chance for every quantum candidate and
  below the aggregate classical controls.
- [`analysis/candidate_freeze.json`](experiments/s2_mechanism_screen/analysis/candidate_freeze.json)
  froze no candidate and set `hardware_authorized=false`.

Alternatives considered: IBM physical validation, Helios-1E emulator validation,
and a Quantinuum physical pilot. All require a frozen candidate under the
governing plan; none exists.

Consequence: S3/S4 provider-facing work is closed for this phase. The branch
records a negative simulator result and does not claim C1, C2, C3, or C4.

## 2026-08-10 — Quantinuum policy remains emulator-only

Decision: retain the non-bypassable physical lock and allow only the exact
`Helios-1E` emulator identifier for any future separately approved campaign.

Evidence: the configured account exposed `Helios-1E` as an emulator; physical
Quantinuum execution is disabled in code and configuration. No HQC cost check
was required because no campaign was authorized.

Consequence: a future emulator campaign must pass the exact syntax/resource
checker and cost-manifest gate before submission. Physical Quantinuum execution
is deferred to the researcher.
