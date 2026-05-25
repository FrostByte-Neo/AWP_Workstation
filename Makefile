PYTHON ?= python3
SKILL_DIR := awp-workstation-skill

.PHONY: verify-workstation verify-workstation-summary

verify-workstation:
	cd $(SKILL_DIR) && $(PYTHON) scripts/verify-workstation.py --strict

verify-workstation-summary:
	cd $(SKILL_DIR) && $(PYTHON) scripts/verify-workstation.py --summary
