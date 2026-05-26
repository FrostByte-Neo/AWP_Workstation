PYTHON ?= python3

.PHONY: test smoke-workstation verify-workstation verify-workstation-summary

test:
	$(PYTHON) -m unittest discover -s tests

smoke-workstation:
	$(PYTHON) -m unittest tests.test_workstation_runtime.WorkstationRuntimeTests.test_operator_smoke_temp_state_root

verify-workstation:
	$(MAKE) test
	$(PYTHON) scripts/verify-workstation.py --strict

verify-workstation-summary:
	$(MAKE) test
	$(PYTHON) scripts/verify-workstation.py --summary
