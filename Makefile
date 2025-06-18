.PHONY: all clean uninstall reinstall test reset venv

VENV_DIR := .venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip
VENV_PYTEST := $(VENV_DIR)/bin/pytest

# Default target
all: reset test

# Ensure the venv exists
venv: $(VENV_PYTHON)

$(VENV_PYTHON):
	@echo "Creating virtual environment in $(VENV_DIR)..."
	@python3 -m venv $(VENV_DIR)
	@$(VENV_PIP) install --upgrade pip setuptools

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	@rm -rf build dist *.egg-info __pycache__ .pytest_cache

# Uninstall the package
uninstall: venv
	@echo "Uninstalling logngine..."
	@$(VENV_PIP) uninstall -y logngine || echo "(Already uninstalled)"

# Reinstall in editable mode
reinstall: venv
	@echo "Installing logngine in editable mode with test extras..."
	@$(VENV_PIP) install -e .[test]

# Run tests
test: venv
	@echo "Running tests..."
	@$(VENV_PYTEST) -v --color=yes --tb=short --maxfail=5

# Reset: clean, uninstall, reinstall
reset: clean uninstall reinstall