.DEFAULT_GOAL := help
.PHONY: help install smoke run aggregate figures test lint typecheck fmt clean

# Use python3 by default (many systems have no bare `python`). Override: make PYTHON=python run
PYTHON ?= python3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev extras
	$(PYTHON) -m pip install -e ".[dev]"

smoke: ## One prompt, one query, one model (Phase 0 acceptance)
	$(PYTHON) -m src.experiment.run --smoke

run: ## Run the full experiment matrix
	$(PYTHON) -m src.experiment.run

aggregate: ## Build summary tables from results.json
	$(PYTHON) -m src.experiment.aggregate

figures: ## Regenerate figures into blog/figures/
	$(PYTHON) -m src.viz.figures

test: ## Run the test suite
	$(PYTHON) -m pytest

lint: ## Lint with ruff
	ruff check src tests

typecheck: ## Type-check with mypy
	mypy src

fmt: ## Auto-format with ruff
	ruff format src tests
	ruff check --fix src tests

clean: ## Remove caches
	rm -rf .pytest_cache .ruff_cache .mypy_cache **/__pycache__
