# English Byte-Matched Pilot Training Configuration

This configuration specifies the parameters used for the English Byte-Matched pretraining run.

## Model Hyperparameters
*   **Architecture**:
    *   `depth`: 6 (layers)
    *   `head_dim`: 64
    *   `window_pattern`: "L" (Full causal attention)
    *   `max_seq_len`: 512
    *   `device_batch_size`: 32
    *   `total_batch_size`: 16,384 tokens
*   **Optimization**:
    *   `num_iterations`: 5,000 steps
    *   `warmup_steps`: 40
    *   `warmdown_ratio`: 0.65
    *   `optimizer`: Muon (matrix parameters) + AdamW (embeddings)
*   **Data and Tokenizer Configuration**:
    *   `NANOCHAT_DATA_DIR`: `/Users/monitsharma/.cache/nanochat/english_data_byte`
    *   `NANOCHAT_TOKENIZER_DIR`: `/Users/monitsharma/.cache/nanochat/tokenizer_english_byte`
