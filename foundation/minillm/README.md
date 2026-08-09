# minillm

`minillm` is the lab's deliberately small, offline educational implementation. It contains character and byte tokenizers, a dataset helper, bigram-ready data flow, causal attention, a tiny transformer language model, generation, and checkpoint helpers. Tests are CPU-compatible and skip cleanly when PyTorch is not installed.

```bash
PYTHONPATH=. python -m pytest foundation/minillm/tests -q
```

This package is not a replacement for the production agent or a reproduction of nanochat. It exists to make tensor shapes and failure modes inspectable.
