# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#  USED FOR TESTING, I.E. FOR DEVELOPING THIS PACKAGE; IF YOU WANT TO INSTALL THIS PACKAGE, JUST USE
#  THE BASIC PIP INSTALLATION. USING THIS MAKEFILE WILL LIKELY CAUSE YOU LOTS OF HEARTACHE AND .VENV
#  TROUBLE.
#
#  TL;DR IF YOU DON'T KNOW WHAT YOU ARE DOING, DON'T RUN THIS MAKEFILE. USE PIP.
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.PHONY: all clean uninstall reinstall test reset venv

VENV_DIR := .venv-linux
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_PYTEST := $(VENV_DIR)/bin/pytest

all: reset test

venv:
	@echo "Creating virtual environment in $(VENV_DIR)..."
	@test -x "$(VENV_PYTHON)" || python3.12 -m venv $(VENV_DIR)
	@$(VENV_PIP) install --upgrade pip setuptools

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build dist *.egg-info __pycache__ .pytest_cache
	@echo "Removing all .so and .pyd files in src/ recursively..."
	@find src -name '*.so' -delete
	@find src -name '*.pyd' -delete

uninstall: venv
	@echo "Uninstalling logngine..."
	@$(VENV_PIP) uninstall -y logngine || echo "(Already uninstalled)"

build: venv
	@echo "Creating pre-build files with build.py..."
	@$(VENV_PIP) install tqdm numpy rtree pint
	@$(VENV_PYTHON) build.py

reinstall: venv build
	@echo "Installing logngine in editable mode with test extras..."
	@$(VENV_PIP) install -e .[test,dev,thermosolver]

test: venv
	@echo "Running tests..."
	@$(VENV_PYTEST) -v --tb=short --maxfail=5

reset: clean uninstall reinstall