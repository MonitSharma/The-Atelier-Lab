# Qwen3-Embedding-4B baseline results

## Step 2 status

**Step 2 — Local Semantic Retrieval: COMPLETE and frozen.**

Step 1 answered “What is this document?” Step 2 answers “Which documents or
passages are most relevant to this query?” The retrieval layer supports
semantic paper search, research memory, retrieval-augmented generation,
cross-paper comparison, note and code search, and context retrieval for larger
reasoning models.

## Frozen model configuration

| Component | Baseline |
|---|---|
| Model | `Qwen3-Embedding-4B` |
| Runtime | Ollama |
| Quantization | `Q4_K_M` |
| Approximate disk size | 2.5 GB |
| Embedding dimension | 2,560 |
| Role | Semantic retrieval only |

The 4B model was selected as the balance between retrieval quality, memory,
storage, speed, and future research-library scale. The 0.6B model was not
needed after storage cleanup, while the 8B model was not worth its additional
resource cost for this baseline.

The model converts text into a 2,560-dimensional vector. It does not generate
conversation, explanations, or summaries.

## Validation set

A small eight-passage benchmark covered QAOA, magic-state distillation, the
newsvendor problem, graph neural networks, VQE, Benders decomposition,
quantum error mitigation, and transformer language models.

The test queries were:

```text
quantum algorithms for optimization
inventory optimization under uncertain demand
fault tolerant quantum resource states
machine learning on graphs
```

This was a domain sanity check rather than a formal information-retrieval
benchmark.

## Initial retrieval results

Raw queries produced sensible broad semantic matches, but the first query
exposed a task-specific ranking problem:

| Query | Rank 1 | Score |
|---|---|---:|
| quantum algorithms for optimization | VQE | 0.7969 |
| inventory optimization under uncertain demand | Newsvendor | 0.8353 |
| fault tolerant quantum resource states | Magic-state distillation | 0.8631 |
| machine learning on graphs | Graph neural networks | 0.8298 |

VQE is related to quantum algorithms, but QAOA was the more direct match for
optimization. This distinguished broad topical similarity from direct
scientific relevance.

## Query-instruction fix

Qwen3 Embedding supports instruction-aware retrieval. The final formatter is:

```python
def format_query(query):
    instruction = (
        "Retrieve passages that are most relevant to the user's scientific "
        "research query. Prefer direct technical relevance over broad topical "
        "similarity. The library primarily contains artificial intelligence, "
        "quantum computing, optimization, operations research, mathematics, "
        "and scientific computing material."
    )

    return f"Instruct: {instruction}\nQuery: {query}"
```

The instruction is applied only to queries. Stored document chunks remain
plain scientific text and are embedded without this query instruction.

## Final retrieval results

| Query | Correct result | Score | Outcome |
|---|---|---:|---|
| quantum algorithms for optimization | QAOA | 0.6592 | Corrected to rank 1 |
| inventory optimization under uncertain demand | Newsvendor | 0.5964 | Remained rank 1 |
| fault tolerant quantum resource states | Magic-state distillation | 0.6049 | Rank 1 with clear margin |
| machine learning on graphs | Graph neural networks | 0.6015 | Remained rank 1 |

For the first query, QAOA moved from rank 2 at 0.7723 to rank 1 at 0.6592.
The lower absolute score is not a regression: ranking quality is the primary
retrieval measure, and scores from differently formatted queries should not be
compared solely by their absolute values.

## Division of responsibility

| Model | Input | Output | Responsibilities |
|---|---|---|---|
| LFM2.5-2.6B | Text | Language / JSON | Characterization, metadata, classification, routing, structured output |
| Qwen3-Embedding-4B | Text | 2,560-dimensional vector | Semantic retrieval, similarity search, research memory, RAG, cross-document discovery |

## Frozen retrieval specification

```text
Documents: plain text embedding
Queries: instruction-aware embedding
Vector size: 2560 dimensions
Primary use: scientific research-library retrieval
```

## Current architecture

```text
PDF ──> PyMuPDF4LLM ──> LFM2.5-2.6B ──> .atelier.json
                                             │
User query ──> retrieval instruction ──> Qwen3-Embedding-4B
                                             │
                                      query vector
                                             │
                                      future vector database
```

## Step 2 completion checklist

- Qwen3-Embedding-4B installation: complete
- Ollama embedding API: complete
- Vector-dimension validation: complete
- Basic semantic retrieval: complete
- Research-domain retrieval: complete
- Initial ranking failure identified: complete
- Query instruction added: complete
- Instruction-aware retest: complete
- Model selection frozen: complete

## Next step

Step 3 will build the local research library: extract papers, create meaningful
chunks, embed them, store the vectors locally, and expose source-returning
search commands such as:

```text
atelier search "finite-time regret bounds for stochastic inventory optimization"
```

Step 2 is complete and frozen before construction of the storage and retrieval
layer.
