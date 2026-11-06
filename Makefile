PYTHON ?= python3
ifeq ($(wildcard .venv/bin/python),)
PYTHON := python3
else
PYTHON := .venv/bin/python
endif

export PYTHONPATH := src
export GX_ANALYTICS_ENABLED := false
export TQDM_DISABLE := 1
export GROCERY_ROOT := $(CURDIR)
export GROCERY_BRONZE := $(CURDIR)/data/bronze
export GROCERY_DUCKDB := $(CURDIR)/data/warehouse/grocery.duckdb

.PHONY: install ingest transform quality test dashboard agent-demo lint ci

install:
	$(PYTHON) -m pip install -r requirements.txt

ingest:
	$(PYTHON) -m grocery_shock.ingest.fetch

transform:
	$(PYTHON) -m grocery_shock transform

quality:
	$(PYTHON) -m grocery_shock quality

dashboard:
	$(PYTHON) -m grocery_shock dashboard

agent-demo:
	$(PYTHON) -m agent.demo --all

lint:
	$(PYTHON) -m ruff check src tests

test: lint
	$(PYTHON) -m pytest

ci: test
