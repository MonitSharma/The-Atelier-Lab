# Experiment 002: Sanskrit vs. English Pilot Study

This experiment investigates how Sanskrit and English differ in tokenizer efficiency, pretraining convergence rates, and generation quality under matched compute and architecture.

## Research Question
*Under matched compute and architecture, how do Sanskrit and English differ in tokenizer efficiency, convergence, and generation quality on a small local transformer?*

---

## Tokenizer Efficiency Results
Custom BPE tokenizers (vocab size = 32,768) were trained on the train splits of the datasets:

| Metric | Sanskrit BPE | English-Byte BPE | English-Char BPE |
| :--- | :--- | :--- | :--- |
| **Raw Bytes** | 52,346,620 | 52,200,179 | 19,249,879 |
| **Unicode Characters** | 19,256,827 | 51,975,022 | 19,182,342 |
| **Lines** | 82,178 | 228,622 | 89,127 |
| **Tokens after BPE** | 8,972,554 | 11,227,580 | 4,126,314 |
| **Bytes per Token** | 5.8341 | 4.6493 | 4.6652 |
| **Characters per Token** | 2.1462 | 4.6292 | 4.6488 |
| **Unique Token Ratio** | 0.0038 | 0.0031 | 0.0083 |

*See [tokenizer_report.md](tokenizer_report.md) for vocabulary utilization, mass concentration, and sparsity metrics, and [data_sources.md](data_sources.md) for dataset quality checks (Devanagari/Latin densities, duplicate line rates).*

---

## Interpretation Rule
> [!WARNING]
> This experiment does **not** support claims such as *"Sanskrit is better for AI."*
> It can only support bounded claims of the form:
> *"Under matched architecture, compute budget, tokenizer size, and dataset construction, Sanskrit showed higher/lower compression, throughput, validation BPB/BPC, and repetition behaviour than English in this small-scale local pretraining setting."*

---

## How to Run the Training

Ensure your environment is set up and activated:
```bash
cd ~/code_projects/nanochat
source .venv/bin/activate
mkdir -p foundation/experiments/002_sanskrit_vs_english_pilot/logs
```

### Run A: English (Byte-Matched) Baseline (73M Model)
```bash
export NANOCHAT_DATA_DIR="$HOME/.cache/nanochat/english_data_byte"
export NANOCHAT_TOKENIZER_DIR="$HOME/.cache/nanochat/tokenizer_english_byte"

caffeinate -i python -m scripts.base_train \
    --depth=6 \
    --head-dim=64 \
    --window-pattern=L \
    --max-seq-len=512 \
    --device-batch-size=32 \
    --total-batch-size=16384 \
    --eval-every=100 \
    --eval-tokens=524288 \
    --core-metric-every=-1 \
    --sample-every=500 \
    --num-iterations=5000 \
    --model-tag="d6_english_byte_pilot" \
    --run=dummy 2>&1 | tee foundation/experiments/002_sanskrit_vs_english_pilot/logs/english_byte_run.log
```

### Run B: Sanskrit Model (73M Model)
```bash
export NANOCHAT_DATA_DIR="$HOME/.cache/nanochat/sanskrit_data"
export NANOCHAT_TOKENIZER_DIR="$HOME/.cache/nanochat/tokenizer_sanskrit"

caffeinate -i python -m scripts.base_train \
    --depth=6 \
    --head-dim=64 \
    --window-pattern=L \
    --max-seq-len=512 \
    --device-batch-size=32 \
    --total-batch-size=16384 \
    --eval-every=100 \
    --eval-tokens=524288 \
    --core-metric-every=-1 \
    --sample-every=500 \
    --num-iterations=5000 \
    --model-tag="d6_sanskrit_pilot" \
    --run=dummy 2>&1 | tee foundation/experiments/002_sanskrit_vs_english_pilot/logs/sanskrit_run.log
```

### Run C: English (Character-Matched) Baseline (73M Model)
```bash
export NANOCHAT_DATA_DIR="$HOME/.cache/nanochat/english_data_char"
export NANOCHAT_TOKENIZER_DIR="$HOME/.cache/nanochat/tokenizer_english_char"

caffeinate -i python -m scripts.base_train \
    --depth=6 \
    --head-dim=64 \
    --window-pattern=L \
    --max-seq-len=512 \
    --device-batch-size=32 \
    --total-batch-size=16384 \
    --eval-every=100 \
    --eval-tokens=524288 \
    --core-metric-every=-1 \
    --sample-every=500 \
    --num-iterations=5000 \
    --model-tag="d6_english_char_pilot" \
    --run=dummy 2>&1 | tee foundation/experiments/002_sanskrit_vs_english_pilot/logs/english_char_run.log
```
