# S2 — controlled mechanism screen

This stage probes interaction order, entanglement family, re-uploading,
feature geometry, spectrum, kernel alignment, and gradient behavior on the
fixed synthetic benchmark. It is exploratory screening only; it does not
freeze candidates or authorize hardware.

An initial bounded local screen over four interaction families, orders 1–4,
q=4, two QIA families, two re-upload counts, and three classical controls is
archived under [`raw/`](raw/) and recorded in
[`screen_validation.json`](screen_validation.json). Its near-chance quantum
scores are exploratory diagnostics only; no candidate was frozen.

The expanded preregistered grid is configured for orders 1–6, q=2/4/6, all
four QIA families, two re-upload counts, and the same classical controls. The
q=2/4 all-order executable panel is also provided in
[`config_orders_1_6.yaml`](config_orders_1_6.yaml); it uses two short training
steps as a bounded diagnostic and should be archived separately under
`raw/orders_1_6/`. This remains a mechanism screen and does not authorize
hardware.

```bash
python -m research.qatelier.experiments.s2_mechanism_screen.screen \
  --config research/qatelier/experiments/s2_mechanism_screen/config.yaml \
  --output-dir /path/to/new/s2-raw
```
