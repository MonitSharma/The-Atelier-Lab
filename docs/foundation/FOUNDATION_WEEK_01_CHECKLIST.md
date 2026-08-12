# Atelier Foundation — Week 1 Checklist

**Dates:** 13–19 August 2026
**Branch:** `atelier-foundation`
**Time budget:** approximately 10–15 focused hours
**Primary milestone:** understand and implement the first pieces of the dense Transformer contract

This is the working checklist for the first week of the from-scratch language-model project. Check items off as you complete them. Do not move to the next section simply because the calendar moved forward; the exit criteria are the gate.

## This week’s objective

By the end of this week, we should have a mathematically understood and tested foundation for `Atelier-D20`:

```text
8 layers · hidden size 384 · 6 query heads · 2 KV heads
head dimension 64 · context 512 · vocabulary 16,000
SwiGLU hidden size 1,024 · approximately 18.7M parameters
```

This week is about the dense model contract. Do not implement MoE, download a large corpus, or start a serious training run yet.

## Working rules

- [ ] Write and understand each implementation personally.
- [ ] Record input and output shapes before writing a component.
- [ ] Add a focused test immediately after each component.
- [ ] Keep `[batch, sequence, hidden]` as the public model layout.
- [ ] Treat `foundation/minillm/` as a reference to study; do not modify it for this milestone.
- [ ] Keep datasets, checkpoints, caches, and large logs outside Git.
- [ ] Make small commits after each completed unit.
- [ ] Record confusion and failed attempts in the learning notes rather than silently skipping them.
- [ ] Do not stage the unrelated overnight-benchmark changes currently present in the worktree.

## Before starting: orient yourself

- [ ] Read the relevant sections of [the full research plan](LOCAL_SPARSE_LANGUAGE_MODEL_RESEARCH_PLAN.md): fair experimental design, architecture proposal, and staged training plan.
- [ ] Read the first sections of [the execution plan](ATELIER_FOUNDATION_EXECUTION_PLAN.md), especially the teacher–builder workflow and Phase 0.
- [ ] Inspect `foundation/minillm/model.py`.
- [ ] Inspect `foundation/minillm/attention.py`.
- [ ] Inspect `foundation/minillm/train.py`.
- [ ] Read the tests under `foundation/minillm/tests/`.
- [ ] Do not modify the existing `minillm` implementation.

After this section, explain in your own words:

- [ ] What an autoregressive language model predicts.
- [ ] Why the causal mask is necessary.
- [ ] Why targets are shifted by one token.
- [ ] What the hidden dimension represents.
- [ ] What a Transformer block receives and returns.
- [ ] How the existing educational model differs from the new research implementation.

## Day 1 — Draw the model contract

- [ ] Draw the complete D20 forward pass on paper.
- [ ] Annotate every tensor with its shape.
- [ ] Define the public input shape: `[B, T]`.
- [ ] Define the embedding shape: `[B, T, D]`.
- [ ] Define the attention shape before and after head reshaping.
- [ ] Define the logits shape: `[B, T, vocabulary]`.
- [ ] Define the target shape: `[B, T]`.
- [ ] Define the loss output as a scalar.
- [ ] Explain the roles of `B`, `T`, `D`, `H`, `H_kv`, and `head_dim`.
- [ ] Decide where flattening from `[B, T, D]` to `[B*T, D]` is permitted.
- [ ] Write down the expected dtype and device behavior.

### Day 1 exit check

- [ ] You can draw the forward pass without looking at the code.
- [ ] You can explain every dimension in the diagram.
- [ ] You can identify where causal masking occurs.

## Day 2 — Derive D20 parameter counts by hand

Use the D20 configuration above.

- [ ] Calculate token-embedding parameters.
- [ ] Calculate Q, K, V, and output-projection parameters for one attention layer.
- [ ] Account for grouped-query attention: 6 query heads and 2 KV heads.
- [ ] Calculate the three SwiGLU projections for one layer.
- [ ] Calculate RMSNorm parameters.
- [ ] Multiply per-layer parameters by eight layers.
- [ ] Calculate the final output projection.
- [ ] Account for tied versus untied embeddings.
- [ ] Add all components together.
- [ ] Compare your result with the expected approximately 18.7M parameters.
- [ ] Write down the formula in a form that can later be tested programmatically.

### Day 2 exit check

- [ ] The hand calculation is correct.
- [ ] You can explain why SwiGLU has three projections.
- [ ] You can explain what tied embeddings save.
- [ ] You can explain why active and total parameters will later differ for MoE.

## Day 3 — Configuration and parameter accounting

Implement only the first small unit: model configuration plus parameter counting.

- [ ] Define a configuration structure for model dimensions.
- [ ] Validate positive layer, width, vocabulary, and context values.
- [ ] Validate that the hidden size is compatible with the attention heads.
- [ ] Validate that the query-head and KV-head relationship is valid for GQA.
- [ ] Validate that the head dimension is consistent with the hidden size.
- [ ] Implement explicit parameter-count formulas.
- [ ] Support tied and untied embeddings in the count.
- [ ] Add a D20 parameter-count test.
- [ ] Add a smaller configuration test.
- [ ] Add an invalid-configuration test.
- [ ] Verify that changing layers, width, vocabulary, or FFN size changes the count predictably.

### Day 3 exit check

- [ ] The programmatic count matches the hand calculation.
- [ ] Invalid configurations fail clearly.
- [ ] Tests pass.
- [ ] The code is readable enough to explain line by line.
- [ ] Commit this unit before continuing.

Suggested commit message:

```text
Add transformer configuration and parameter accounting
```

## Day 4 — Understand RMSNorm

Study RMSNorm before implementing it.

- [ ] Write the RMSNorm equation in your notes.
- [ ] Explain how RMSNorm differs from LayerNorm.
- [ ] Explain why RMSNorm does not subtract the mean.
- [ ] Explain the role of epsilon.
- [ ] Explain the role of the learnable scale parameter.
- [ ] Work through a small vector manually.
- [ ] Predict the output for a zero vector and a constant vector.

## Day 5 — Implement and test RMSNorm

- [ ] Implement the smallest correct RMSNorm module.
- [ ] Preserve the input shape.
- [ ] Preserve the intended device.
- [ ] Preserve or deliberately document the intended dtype behavior.
- [ ] Test output shape.
- [ ] Test finite output values.
- [ ] Test zero and constant inputs.
- [ ] Test gradients.
- [ ] Compare one small result with a hand calculation.
- [ ] Run the test on CPU.
- [ ] Run the test on MPS if the local PyTorch installation supports it.
- [ ] Check that the implementation performs no accidental CPU transfer.

### Day 5 exit check

- [ ] RMSNorm is mathematically understood.
- [ ] RMSNorm tests pass.
- [ ] CPU behavior is verified.
- [ ] MPS behavior is verified or the limitation is recorded.
- [ ] Commit this unit before starting another component.

Suggested commit message:

```text
Implement and test RMSNorm
```

## Optional stretch goal — derive RoPE

Only begin this section if the previous sections are complete and tested.

- [ ] Read the RoPE section of the research plan.
- [ ] Explain why rotating query and key vectors can represent relative position.
- [ ] Derive the two-dimensional rotation equations.
- [ ] Work through one small numerical example.
- [ ] Decide the expected cosine and sine table shapes.
- [ ] Write the input and output shape contract.
- [ ] Stop if the derivation is unclear; RoPE implementation belongs to next week.

Do not sacrifice the configuration and RMSNorm exit gates to complete this stretch goal.

## End-of-week definition of done

- [ ] You can explain the D20 architecture without relying on the document.
- [ ] The hand-derived D20 parameter count is correct.
- [ ] The configuration validates incompatible dimensions.
- [ ] The programmatic parameter count matches the hand calculation.
- [ ] Configuration tests pass.
- [ ] RMSNorm is implemented and tested.
- [ ] CPU/MPS behavior is understood or documented.
- [ ] At least two small, focused commits exist.
- [ ] A short learning note describes what you understand and what remains unclear.
- [ ] No MoE code has been written.
- [ ] No large dataset has been downloaded.
- [ ] No serious training run has been started.

## Session record

Use this section as a lightweight log. Add one entry after each session.

| Date | What I learned | What I implemented | Tests/results | What remains unclear |
|---|---|---|---|---|
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |
|  |  |  |  |  |

## Review questions for the teacher

Bring these questions, along with your code and test output, to the next review:

1. Does my parameter-count derivation account for every trainable tensor?
2. Are my tensor shapes and head reshapes correct?
3. Are my configuration validation rules too strict or too permissive?
4. Does my RMSNorm implementation match the equation numerically?
5. Are my tests checking behavior, rather than only checking that code runs?
6. What should I improve before implementing RoPE?

The next milestone begins only after the end-of-week definition of done is satisfied.
