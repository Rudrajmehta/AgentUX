#!/usr/bin/env bash
# AgentUX install script.
#
# Detects OS, checks Python 3.12+, installs agentux via pip,
# optionally installs Playwright chromium, and prints next steps.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Rudrajmehta/AgentUX/main/scripts/install.sh | bash
#
# Or run locally:
#   ./scripts/install.sh

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

info()  { echo -e "${GREEN}[agentux]${RESET} $*"; }
warn()  { echo -e "${YELLOW}[agentux]${RESET} $*"; }
error() { echo -e "${RED}[agentux]${RESET} $*"; }

# --- Detect OS ---
OS="$(uname -s)"
case "${OS}" in
  Darwin) info "Detected macOS" ;;
  Linux)  info "Detected Linux" ;;
  *)      error "Unsupported OS: ${OS}. AgentUX supports macOS and Linux."; exit 1 ;;
esac

# --- Check Python ---
PYTHON=""
for candidate in python3.13 python3.12 python3; do
  if command -v "${candidate}" &>/dev/null; then
    PYTHON="${candidate}"
    break
  fi
done

if [ -z "${PYTHON}" ]; then
  error "Python 3.12+ is required but not found."
  error "Install Python from https://www.python.org/downloads/"
  exit 1
fi

PY_VERSION=$("${PYTHON}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("${PYTHON}" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("${PYTHON}" -c "import sys; print(sys.version_info.minor)")

if [ "${PY_MAJOR}" -lt 3 ] || { [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -lt 12 ]; }; then
  error "Python 3.12+ is required. Found ${PY_VERSION}."
  exit 1
fi

info "Using ${PYTHON} (${PY_VERSION})"

# --- Install agentux ---
info "Installing agentux..."
"${PYTHON}" -m pip install --upgrade pip --quiet
"${PYTHON}" -m pip install agentux --quiet

if ! command -v agentux &>/dev/null; then
  warn "agentux command not found on PATH."
  warn "You may need to add your Python scripts directory to PATH."
  warn "Try: export PATH=\"\$(${PYTHON} -m site --user-base)/bin:\${PATH}\""
fi

info "agentux installed successfully."

# --- Optional: Playwright ---
echo ""
# Detect if running interactively or piped
if [ -t 0 ]; then
  read -r -p "Install Playwright chromium for browser evaluations? [Y/n] " INSTALL_PW
  INSTALL_PW="${INSTALL_PW:-Y}"
else
  # Non-interactive (piped from curl): skip Playwright by default
  INSTALL_PW="n"
  info "Non-interactive mode: skipping Playwright install. Run later: playwright install chromium"
fi

if [[ "${INSTALL_PW}" =~ ^[Yy]$ ]]; then
  info "Installing Playwright chromium..."
  "${PYTHON}" -m playwright install chromium
  info "Playwright chromium installed."
else
  warn "Skipping Playwright. Browser evaluations will not work until you run:"
  warn "  playwright install chromium"
fi

# --- Next steps ---
echo ""
echo -e "${BOLD}Next steps:${RESET}"
echo "  1. Set an API key:  export OPENAI_API_KEY=\"sk-...\""
echo "  2. Verify install:  agentux doctor"
echo "  3. Try a demo run:  agentux run https://example.com --surface browser --task \"Find the heading\" --demo"
echo ""
echo "  Docs: https://github.com/Rudrajmehta/AgentUX/tree/main/docs"
echo ""
