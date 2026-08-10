# S2 — controlled mechanism screen

This stage probes interaction order, entanglement family, re-uploading,
feature geometry, spectrum, kernel alignment, and gradient behavior on the
fixed synthetic benchmark. It is exploratory screening only; it does not
freeze candidates or authorize hardware.

A bounded local screen over four interaction families, orders 1–4, q=4, two
QIA families, two re-upload counts, and three classical controls is archived
under [`raw/`](raw/) and recorded in
[`screen_validation.json`](screen_validation.json). Its near-chance quantum
scores are exploratory diagnostics only; no candidate was frozen.

```bash
python -m research.qatelier.experiments.s2_mechanism_screen.screen \
  --config research/qatelier/experiments/s2_mechanism_screen/config.yaml \
  --output-dir /path/to/new/s2-raw
```
