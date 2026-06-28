# M3 Pro Nanochat Baseline Configuration

This document captures the system specifications, model architectures, and training hyperparameters used for the overnight benchmarks.

## System Specifications
*   **Hardware Model**: MacBook Pro 16-inch (Space Black)
*   **CPU**: Apple M3 Pro (12 cores: 6 performance, 6 efficiency)
*   **GPU**: 18-Core GPU
*   **Memory**: 36 GB Unified Memory
*   **Storage**: 512 GB SSD
*   **OS Version**: macOS Sequoia (Darwin 26.5.1 equivalent)
*   **PyTorch Version**: 2.9.1
*   **Device Type**: MPS (Metal Performance Shaders)

---

## Step 1: Tokenizer Training Configuration
*   **Dataset**: ClimbMix Parquets
*   **Max Characters**: 2,000,000,000
*   **Vocab Size**: 32,768 (BPE)
*   **Document Cap**: 10,000 characters

---

## Step 2: 73M Baseline Model Configuration
*   **Architecture**:
    *   `sequence_len`: 512
    *   `vocab_size`: 32,768
    *   `n_layer`: 6
    *   `n_head`: 6
    *   `n_kv_head`: 6
    *   `n_embd`: 384
    *   `window_pattern`: "L" (Full causal attention)
*   **Parameters**:
    *   `wte`: 12,582,912
    *   `value_embeds`: 37,748,736
    *   `lm_head`: 12,582,912
    *   `transformer_matrices`: 10,617,048
    *   `total`: 73,531,620 (73.5M parameters total)
*   **Hyperparameters**:
    *   `total_batch_size`: 16,384 tokens
    *   `device_batch_size`: 32 sequences (16,384 tokens, gradient accumulation steps = 1)
    *   `num_iterations`: 5,000
    *   `optimizer`: Muon (matrix parameters) + AdamW (embeddings)
    *   `Muon lr`: Scaled by 0.1768 to 0.02
    *   `AdamW lr`: Scaled ∝ 1/√(384/768) to 0.3
    *   `weight_decay`: Scaled from 0.28 to 0.234903

---

## Step 3: 286M Scale-Up Model Configuration
*   **Architecture**:
    *   `sequence_len`: 512
    *   `vocab_size`: 32,768
    *   `n_layer`: 12
    *   `n_head`: 12
    *   `n_kv_head`: 12
    *   `n_embd`: 768
    *   `window_pattern`: "L" (Full causal attention)
*   **Parameters**:
    *   `wte`: 25,165,824
    *   `value_embeds`: 150,994,944
    *   `lm_head`: 25,165,824
    *   `transformer_matrices`: 84,935,520
    *   `total`: 286,262,136 (286.2M parameters total)
*   **Hyperparameters**:
    *   `total_batch_size`: 16,384 tokens
    *   `device_batch_size`: 16 sequences (8,192 tokens, gradient accumulation steps = 2)
    *   `num_iterations`: 5,000
    *   `optimizer`: Muon (matrix parameters) + AdamW (embeddings)
    *   `Muon lr`: Scaled by 0.1768 to 0.02
    *   `AdamW lr`: Scaled ∝ 1/√(768/768) to 0.3
    *   `weight_decay`: Scaled from 0.28 to 0.049497
