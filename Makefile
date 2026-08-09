.DEFAULT_GOAL := check
.PHONY: check test validate summarize

check:
	python3 scripts/check_repo.py

validate:
	python3 scripts/validate_experiments.py

summarize:
	python3 scripts/summarize_results.py

test:
	python3 -m pytest -q
