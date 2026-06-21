# Atelier — common tasks. Run `make help` for the list.
.DEFAULT_GOAL := help
SHELL := /bin/bash
PY := .venv/bin/python
export ATELIER_NO_BANNER := 1

.PHONY: help setup test ingest eval eval-plots planner-data route-eval train-router demo mcp reproduce clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install deps (+ editable package)
	uv venv && uv pip install -r requirements.txt && uv pip install -e .

test: ## Run the fast unit suite (no model)
	$(PY) -m pytest -q

ingest: ## Index the sample corpus
	$(PY) -m atelier.cli ingest ./Project.md ./README.md ./myNotes.md

eval: ## Run the reliability eval (both modes)
	$(PY) -m atelier.cli eval --mode all

eval-plots: ## Generate SVG plots from the latest eval report
	$(PY) -m atelier.cli eval-plots

planner-data: ## Build planner-router SFT data from eval metadata
	$(PY) models/router/make_planner_dataset.py

route-eval: ## Measure routing savings on the doc-QA suite
	$(PY) -m eval.route_eval

train-router: ## Generate data + LoRA-fine-tune the router model
	$(PY) models/router/make_dataset.py
	$(PY) -m mlx_lm lora --model mlx-community/Qwen2.5-0.5B-Instruct-4bit --train \
	  --data models/router/data --iters 200 --batch-size 4 --num-layers 8 \
	  --mask-prompt --adapter-path models/router/adapter
	$(PY) -m models.router.evaluate

demo: ## A quick end-to-end build-mode demo
	$(PY) -m atelier.cli agent "Fix the failing test in sample_task/ and prove it passes"

mcp: ## Serve the toolbox over MCP (stdio)
	$(PY) -m atelier.cli mcp

reproduce: ## Full one-command reproduction
	bash scripts/reproduce.sh

clean: ## Remove runtime data + caches (keeps the trained adapter)
	rm -rf .eval_workspace data/traces data/eval_reports .pytest_cache **/__pycache__
