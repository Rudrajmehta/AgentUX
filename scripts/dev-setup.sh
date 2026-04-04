#!/usr/bin/env bash
# Developer setup script for AgentUX.
#
# Creates a virtual environment, installs dev dependencies,
# installs Playwright, and runs the test suite.
#
# Usage:
#   ./scripts/dev-setup.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${GREEN}[dev-setup]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[dev-setup]${RESET} $*"; }
error() { echo -e "${RED}[dev-setup]${RESET} $*"; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

info "Repository root: ${REPO_ROOT}"

# --- Check Python ---
PYTHON=""
for candidate in python3.13 python3.12 python3; do
  if command -v "${candidate}" &>/dev/null; then
    PY_MINOR=$("${candidate}" -c "import sys; print(sys.version_info.minor)")
    PY_MAJOR=$("${candidate}" -c "import sys; print(sys.version_info.major)")
    if [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -ge 12 ]; then
      PYTHON="${candidate}"
      break
    fi
  fi
done

if [ -z "${PYTHON}" ]; then
  error "Python 3.12+ is required but not found."
  exit 1
fi

PY_VERSION=$("${PYTHON}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Using ${PYTHON} (${PY_VERSION})"

# --- Create venv ---
if [ -d ".venv" ]; then
  info "Virtual environment .venv already exists, reusing it."
else
  info "Creating virtual environment..."
  "${PYTHON}" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
info "Activated .venv"

# --- Install deps ---
info "Upgrading pip..."
pip install --upgrade pip --quiet

info "Installing agentux with dev dependencies..."
pip install -e ".[dev]" --quiet

# --- Playwright ---
info "Installing Playwright chromium..."
python -m playwright install chromium

# --- Lint check ---
info "Running ruff check..."
if ruff check src/ tests/; then
  info "Lint passed."
else
  warn "Lint issues found. Run 'ruff check --fix src/ tests/' to auto-fix."
fi

# --- Type check ---
info "Running mypy..."
if mypy; then
  info "Type check passed."
else
  warn "Type check issues found."
fi

# --- Tests ---
info "Running tests..."
if pytest; then
  info "All tests passed."
else
  warn "Some tests failed. Review output above."
fi

echo ""
echo -e "${BOLD}Dev setup complete.${RESET}"
echo "  Activate the venv:  source .venv/bin/activate"
echo "  Run tests:          pytest"
echo "  Lint:               ruff check src/ tests/"
echo "  Type check:         mypy"
echo ""
