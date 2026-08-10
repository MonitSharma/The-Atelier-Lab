.DEFAULT_GOAL := check
.PHONY: check test validate summarize qatelier-test qatelier-smoke qatelier-validate qatelier-hardware-preflight qatelier-s0 qatelier-baselines qatelier-screen qatelier-heldout qatelier-noise qatelier-analyze qatelier-paper qatelier-audit qatelier-reproduce

check:
	python3 scripts/check_repo.py

validate:
	python3 scripts/validate_experiments.py

summarize:
	python3 scripts/summarize_results.py

test:
	python3 -m pytest -q

qatelier-test:
	python3 -m pytest research/qatelier/tests -q

qatelier-validate:
	python3 -m research.qatelier.cli validate --structure-only --json

qatelier-smoke:
	python3 -m research.qatelier.cli smoke --output research/qatelier/artifacts/smoke/result.json

qatelier-hardware-preflight:
	python3 -m research.qatelier.cli hardware-preflight --json

qatelier-s0:
	python3 -m research.qatelier.cli prepare-data

qatelier-baselines:
	python3 -m research.qatelier.cli baseline

qatelier-screen:
	python3 -m research.qatelier.cli quantum

qatelier-heldout:
	python3 -m research.qatelier.cli quantum

qatelier-noise:
	python3 -m research.qatelier.cli quantum

qatelier-analyze:
	python3 -m research.qatelier.cli analyze

qatelier-paper:
	python3 -m research.qatelier.cli paper

qatelier-audit:
	python3 -m research.qatelier.cli audit

qatelier-reproduce:
	python3 -m research.qatelier.cli reproduce
