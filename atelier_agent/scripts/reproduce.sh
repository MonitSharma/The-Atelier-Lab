#!/usr/bin/env bash
# Atelier — one-command reproduction.
# Sets up the env, pulls models, runs the tests, ingests the sample corpus,
# runs the reliability eval, and trains + evaluates the router. Everything local.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export ATELIER_NO_BANNER=1

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }

say "[1/6] Python environment (uv)"
command -v uv >/dev/null || { echo "Please install uv: https://github.com/astral-sh/uv"; exit 1; }
[ -d .venv ] || uv venv
# shellcheck disable=SC1091
source .venv/bin/activate
uv pip install -q -r requirements.txt
uv pip install -q -e .

say "[2/6] Ollama models"
command -v ollama >/dev/null || { echo "Please install + start Ollama: https://ollama.com"; exit 1; }
for m in qwen3:14b qwen3:4b; do
  ollama list | grep -q "$m" || ollama pull "$m"
done

say "[3/6] Unit tests"
pytest -q

say "[4/6] Ingest the frozen sample corpus"
atelier ingest ./eval/fixtures/docqa_corpus/Project.md ./README.md ./eval/fixtures/docqa_corpus/myNotes.md

say "[5/6] Reliability eval (both modes)"
atelier eval --mode all

say "[6/6] Router: train if needed, then measure the fine-tune"
if [ ! -f models/router/adapter/adapters.safetensors ]; then
  python models/router/make_dataset.py
  python -m mlx_lm lora --model mlx-community/Qwen2.5-0.5B-Instruct-4bit --train \
    --data models/router/data --iters 200 --batch-size 4 --num-layers 8 \
    --mask-prompt --adapter-path models/router/adapter
fi
python -m models.router.evaluate

say "Done. Reports in data/eval_reports/ — see ../docs/CURRENT_RESULTS.md."
