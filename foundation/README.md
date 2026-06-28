# Foundation Layer

This folder houses the core research, implementations, and experiments for building and training foundation models from first principles within **The Atelier Lab**.

The goal of this layer is to implement, evaluate, and scale local architectures on consumer hardware (specifically Apple Silicon).

---

*   **`datasets/`**: Active dataset sharding pipelines, curation rules, and BPE tokenization.
    *   [**`sanskritpile/`**](file:///Users/monitsharma/code_projects/The-Atelier-Lab/foundation/datasets/sanskritpile/): Multi-version curated Sanskrit corpora and tokenizer reporting.
    *   [**`english/`**](file:///Users/monitsharma/code_projects/The-Atelier-Lab/foundation/datasets/english/): Character-matched and byte-matched English baseline dataset metadata.
*   **`experiments/`**: Systematic empirical runs, log archives, configuration files, and analytical reports.
    *   [**`000_m3pro_nanochat_baseline/`**](file:///Users/monitsharma/code_projects/The-Atelier-Lab/foundation/experiments/000_m3pro_nanochat_baseline/): Initial baseline benchmark measuring hardware capabilities and model capacity scaling of `nanochat` on an Apple M3 Pro.
    *   [**`001_73m_longer_training/`**](file:///Users/monitsharma/code_projects/The-Atelier-Lab/foundation/experiments/001_73m_longer_training/): Ongoing/planned run to isolate whether generation repetition in small networks is an undertraining issue or a capacity constraint.
    *   [**`002_sanskrit_vs_english_pilot/`**](file:///Users/monitsharma/code_projects/The-Atelier-Lab/foundation/experiments/002_sanskrit_vs_english_pilot/): Sanskrit vs. English comparison study (character-matched vs. byte-matched pretraining).
*   *Future Implementation Layers (Planned)*:
    *   `tokenizers/`: Custom Byte Pair Encoding (BPE) definitions and vocab training scripts.
    *   `models/`: Autoregressive transformer block architecture definitions.
    *   `training/`: Custom pre-training loop implementation with support for optimized kernels (e.g. Muon, AdamW).
    *   `inference/`: Local token-streaming and generation engine scripts.
    *   `evaluation/`: Automatic benchmarks (loss tracking, downstream metrics).

---

## Research Milestones

### 📈 Hardware Scaling Law (Experiment 000)
Our baseline study on the Apple M3 Pro (12-Core CPU, 18-Core GPU, 36GB Unified Memory) established the local baseline for training throughput using PyTorch's Metal Performance Shaders (MPS):

| Model Tag | Parameters | Throughput (tok/sec) | Compute Cost (per 5k steps) | Final Loss (BPB) |
| :--- | :--- | :--- | :--- | :--- |
| **73M nanochat baseline** | 73.5 Million | **~18,700** | ~1.2 hours | 1.1664 |
| **286M nanochat scale-up**| 286.2 Million| **~4,470** | ~5.1 hours | 1.0954 |

### 🛠 Active Investigation Areas
1.  **Generation Repetition**: Observing severe repeating loops in generated base model output. Currently launching longer training runs to determine when or if the loss drop breaks repetition cycles.
2.  **Metal Kernel Optimizations**: Identifying pathways to run training in FP16/BF16 mixed-precision on MPS to increase raw training throughput.
