# S3 — held-out and OOD protocol

S3 is preregistered but intentionally not executed in the current phase. The
negative S2 screen froze no quantum candidate, so running an OOD evaluation
would not be a valid frozen quantum comparison.

The locked OOD condition is IMDb sentiment, evaluated after training on the
frozen SST-2 protocol. The source revision, member hashes, label mapping, and
test-only evaluation rule are in [`ood_manifest.json`](ood_manifest.json).

The decision record is [`decision.json`](decision.json). It explicitly records
that no OOD rows or provider jobs were used. A future run must start from a new
approved preregistration and cannot use IMDb results for architecture,
compressor, or candidate selection.
