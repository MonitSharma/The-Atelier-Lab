# LFM2.5-2.6B baseline results

## Step 1 status

**Step 1 — Local Worker Model and Fast Paper Characterization: COMPLETE and frozen.**

This benchmark established the first local worker for the Atelier Workbench:

- fast routine inference;
- structured extraction and classification;
- fast research-paper characterization;
- strict machine-readable output for future routing and automation.

The worker is not the primary scientific reasoning model. Its role is to decide what should happen next and prepare clean inputs for stronger models.

## Hardware and runtime

| Component | Baseline |
|---|---|
| Machine | MacBook Pro with Apple M3 Pro |
| Unified memory | 36 GiB |
| Runtime | Ollama 0.32.5 |
| Initial free disk reported during run | approximately 161 GB |
| Existing large-model baseline | `gemma4:26b`, 17 GB |

## Model installation

```text
hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K
```

Q6_K was selected because the model is already small enough to fit comfortably, making additional precision inexpensive compared with an aggressive Q4 quantization.

Ollama reported:

```text
NAME                                    SIZE      PROCESSOR    CONTEXT
hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q6_K   3.0 GB    100% GPU     32768
```

The model was fully resident on the GPU with no CPU/GPU split. The 32,768-token context was retained as sufficient for worker tasks; the context was not increased because large contexts consume unified memory unnecessarily.

## Baseline inference test

The model was asked to explain the importance of eigenvalues in quantum computing and optimization.

```text
Prompt tokens:       26
Output tokens:       1421
Prompt processing:   368.4 tokens/s
Generation:          52.9 tokens/s
Total time:          27.14 s
```

### Finding

Raw inference speed was strong for a 2.6B local model on the M3 Pro. The primary failure was instruction following: a request for approximately 150 words produced 1,421 output tokens.

### Harness requirement

Output length and structure must not depend only on natural-language instructions. The future harness needs explicit output limits, schemas, constrained enumerations, and deterministic validation.

## Structured scientific classification

The model classified a synthetic abstract involving parameterized quantum circuits, graph neural networks, maximum independent set, and IBM quantum hardware.

The first structured result correctly identified:

- quantum computing;
- combinatorial optimization;
- maximum independent set;
- GNN-assisted circuit initialization;
- high quantum relevance;
- high optimization relevance;
- experimental evaluation.

The initial error was:

```json
"theoretical": true
```

The abstract did not explicitly contain a theorem, proof, mathematical bound, formal guarantee, complexity result, or analytical derivation.

The prompt was strengthened with an explicit definition:

```text
theoretical=true ONLY if the supplied text explicitly contains
a theorem, proof, mathematical bound, formal guarantee,
complexity result, analytical derivation, or another
theoretical result.
```

The result then correctly changed to:

```json
"theoretical": false,
"experimental": true
```

### Schema failure

Generic JSON mode produced syntactically valid JSON but violated semantic constraints. For example, the model returned:

```json
"relevance_to_quantum": "high (uses parameterized quantum circuits)"
```

instead of the required enum value:

```json
"relevance_to_quantum": "high"
```

It also omitted the required `confidence` field.

### Schema-constrained result

The Ollama request was upgraded to a complete JSON Schema requiring every field, exact enums, boolean types, confidence, and no additional properties.

```json
{
  "domain": "quantum computing / combinatorial optimization",
  "subfield": "hybrid quantum-classical algorithms for optimization",
  "problem": "maximum independent set (MIS) problems on graphs",
  "method": "Hybrid algorithm using parameterized quantum circuits + graph neural network for initialization",
  "theoretical": false,
  "experimental": true,
  "relevance_to_quantum": "high",
  "relevance_to_ai": "medium",
  "relevance_to_optimization": "high",
  "confidence": "high"
}
```

Performance for the schema-constrained result:

```text
Prompt tokens:   252
Output tokens:   127
Generation:      48.5 tokens/s
```

### Classification conclusion

LFM2.5 is approved as a reliable local worker when used behind a strict harness. The harness and model must be evaluated together.

## Fast Paper Characterization v0.1

The first practical Atelier feature used this pipeline:

```text
PDF
 ↓
PyMuPDF4LLM deterministic extraction
 ↓
structured Markdown
 ↓
opening high-information portion
 ↓
LFM2.5
 ↓
JSON Schema
 ↓
research characterization card
```

The test paper was:

**Data-Driven Newsvendor Problem: Performance of the Sample Average Approximation**

### Initial extraction findings

The full-document extraction recovered the title, authors, abstract, introduction, section text, references, and much of the mathematical prose. Problems included:

- poorly reconstructed first-page publisher/author metadata;
- damaged mathematical notation such as `O(log N)`, `O(√N)`, `Ω(log N)`, and `Ω(√N)`;
- unnecessary Tesseract OCR on a later page even though the fast workflow only needed the opening portion.

### Initial characterization error

The first paper card incorrectly contaminated the paper's `DOMAIN` with the user's interests in AI, quantum computing, and optimization.

The architecture was corrected by separating:

```text
WHAT IS THE PAPER?
  domain, subfield, research_problem, method, main_claim

IS IT USEFUL TO THE USER?
  ai_relevance, quantum_relevance, optimization_relevance,
  why_relevant, recommended_action
```

User interests may influence relevance fields only. They must not change the objective characterization of the paper itself.

## Fast PDF optimization

The initial implementation processed the complete PDF and only then truncated the extracted text to 18,000 characters. The workflow was changed to use only the first four pages:

```python
fast_pages = [0, 1, 2, 3]
```

Native extraction is attempted first with OCR disabled. OCR is used only if the extracted content is too sparse:

```text
first four pages
       ↓
native extraction
       ↓
enough useful text?
    /           \
  yes            no
   │              │
continue      retry with OCR
```

This is intentionally different from a future Deep Read workflow.

## Final Fast Paper v0.1 result

```text
Reading: Data-Driven Newsvendor Problem.pdf
Extracted 20,885 characters in 0.93s
Using 18,000 characters for fast characterization
Running local LFM worker...
```

Final characterization:

```text
TITLE
Data-Driven Newsvendor Problem:
Performance of the Sample Average Approximation

TYPE
theoretical

DOMAIN
Operations Research, Supply Chain Management, Stochastic Optimization

SUBFIELDS
• Operations Research
• Stochastic Optimization
• Inventory Control

RESEARCH PROBLEM
Performance analysis of sample average approximation (SAA)
for the data-driven newsvendor problem under minimal separation
assumptions on demand distribution flatness.

METHOD
Theoretical analysis with mathematical derivations, including
lower and upper bounds on worst-case regret.

MAIN CLAIM
SAA achieves near-optimal asymptotic regret bounds:
O(log N) under the minimal separation assumption and O(√N)
without it.

PROFILE
Theoretical:  True
Experimental: False

RELEVANCE
AI:           low
Quantum:      none
Optimization: high

RECOMMENDED ACTION
READ

CONFIDENCE
high
```

The structured output was automatically written to:

```text
Data-Driven Newsvendor Problem.atelier.json
```

Final performance:

```text
PDF extraction:   0.93 s
LFM inference:    12.56 s
Generation:       49.6 tokens/s
Prompt tokens:    4499
Output tokens:    365
```

### Measured improvement

PDF extraction latency decreased from 4.57 seconds to 0.93 seconds:

```text
approximately 79.6% faster
```

The local inference stage remained approximately 12–14 seconds for a roughly 4,500-token scientific prompt.

## Approved and unapproved responsibilities

### Approved for LFM2.5

```text
✓ task routing
✓ file classification
✓ paper characterization
✓ metadata extraction
✓ structured JSON generation
✓ lightweight summaries
✓ query rewriting
✓ basic relevance estimation
✓ preprocessing for larger models
```

### Route elsewhere

```text
✗ difficult mathematics
✗ detailed theoretical verification
✗ deep paper review
✗ subtle scientific judgments
✗ novel research conclusions
✗ high-stakes factual interpretation
```

Those tasks should later be routed to stronger local or frontier models.

## Frozen baseline

```text
Model:                         LFM2.5-2.6B Q6_K
Loaded size:                   approximately 3.0 GB
Processor:                     100% GPU
Context:                       32,768 tokens
Typical generation:            approximately 49–53 tokens/s
Fast PDF extraction:           approximately 0.9 seconds
Fast characterization:         approximately 12–14 seconds
Output:                        strict structured JSON
```

## Current architecture after Step 1

```text
                    ATELIER WORKBENCH
                           │
                           ▼
                     PDF / TEXT INPUT
                           │
                           ▼
                    PyMuPDF4LLM
                 deterministic extraction
                           │
                           ▼
                     LFM2.5-2.6B
                      local worker
                           │
                           ▼
                      JSON Schema
                           │
                           ▼
                  FAST PAPER CARD
                           │
                           ▼
                   .atelier.json
```

## Lessons carried forward

1. **Harness quality matters.** Precise definitions, JSON Schema, enum constraints, and output limits substantially improve a small model without changing its weights.
2. **Deterministic tools come first.** Extract and normalize a PDF before asking an LLM to reason about it.
3. **Fast characterization is not Deep Read.** The fast path answers what the paper is, what it does, how relevant it is, and whether it deserves deeper investigation.
4. **Objective identity and personal relevance must remain separate.** Personalization belongs in relevance and recommendation fields, not in the paper's domain or method.

## Next step

The next component is the local semantic-retrieval layer: embeddings, semantic paper search, research memory, cross-paper comparison, and retrieval-augmented generation.

The run notes proposed `Qwen3-Embedding-4B` as the next experiment. The current workbench roster starts with `Qwen3-Embedding-0.6B` as the compact baseline and treats the 4B model as an upgrade if retrieval evaluation shows that the smaller model is insufficient.
