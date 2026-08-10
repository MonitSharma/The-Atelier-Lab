.DEFAULT_GOAL := check
QATELIER_PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
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
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests -q

qatelier-validate:
	$(QATELIER_PYTHON) -m research.qatelier.cli validate --structure-only --json

qatelier-smoke:
	$(QATELIER_PYTHON) -m research.qatelier.cli smoke --output research/qatelier/artifacts/smoke/result.json

qatelier-hardware-preflight:
	python3 -m research.qatelier.cli hardware-preflight --json

qatelier-s0:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_s0_protocol.py research/qatelier/tests/test_s0_splits.py research/qatelier/tests/test_s0_analysis.py -q

qatelier-baselines:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_s1_baseline_lock.py research/qatelier/tests/test_s1_mrpc_manifest.py research/qatelier/tests/test_s1_scientific_retrieval.py research/qatelier/tests/test_s1_controlled_order.py -q

qatelier-screen:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_s2_screen.py -q

qatelier-heldout:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_s3_heldout.py -q

qatelier-noise:
	$(QATELIER_PYTHON) -c "print('QAtelier noise/hardware gate: not authorized because no candidate was frozen; see research/qatelier/FINAL_RESEARCH_REPORT.md')"

qatelier-analyze:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_audit.py research/qatelier/tests/test_s0_analysis.py research/qatelier/tests/test_s2_screen.py -q

qatelier-paper:
	test -s research/qatelier/FINAL_RESEARCH_REPORT.md
	test -s research/qatelier/manuscript/qatelier_draft.md
	test -s research/qatelier/manuscript/REPRODUCIBILITY_APPENDIX.md

qatelier-audit:
	$(QATELIER_PYTHON) -m pytest research/qatelier/tests/test_audit.py -q

qatelier-reproduce:
	$(MAKE) qatelier-test
	$(MAKE) qatelier-validate
	$(MAKE) qatelier-s0
	$(MAKE) qatelier-baselines
	$(MAKE) qatelier-screen
	$(MAKE) qatelier-heldout
	$(MAKE) qatelier-analyze
	$(MAKE) qatelier-paper
	$(MAKE) qatelier-audit
