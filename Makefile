.PHONY: setup test test-sol test-py test-all clean

PYTHON ?= python3.12
VENV   := agents/.venv
FORGE  := $(HOME)/.foundry/bin/forge

# ── One-command setup ──────────────────────────────────────────────
setup: $(VENV)/.installed contracts/out

$(VENV)/.installed: agents/pyproject.toml agents/requirements-lock.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip -q
	$(VENV)/bin/pip install -r agents/requirements-lock.txt -q
	$(VENV)/bin/pip install -e agents/.[dev] --no-deps -q
	touch $@

contracts/out: contracts/src/*.sol
	cd contracts && $(FORGE) build

# ── Tests ──────────────────────────────────────────────────────────
test: test-all

test-sol: contracts/out
	cd contracts && $(FORGE) test

test-py: $(VENV)/.installed contracts/out
	cd agents && ../$(VENV)/bin/python -m pytest -q

test-all: test-sol test-py

# ── Clean ──────────────────────────────────────────────────────────
clean:
	rm -rf $(VENV) contracts/out contracts/cache
