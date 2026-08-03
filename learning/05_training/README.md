# 05 — Training

**Concept.** AdamW updates weights; schedules, warmup, clipping, accumulation, validation, and checkpoints control a run. **Background.** Gradients and basic optimization. **Shapes.** Gradients match parameters; scalar loss is reduced over tokens.

**Task.** Train on the committed fixture with a fixed seed and save a checkpoint. **Verify.** Loading it reproduces the next validation loss. **Mistakes.** Saving only weights, validating with gradients enabled, and changing the seed unnoticed.

**Production connection.** `foundation/minillm/train.py` keeps the loop readable before scale. **Read.** AdamW and reproducibility guidance. **Exit.** Resume a run and document what is and is not deterministic on MPS.
