#!/usr/bin/env bash
# Example: Evaluate a website's agent usability with AgentUX.
#
# Prerequisites:
#   - agentux installed (pip install agentux)
#   - OPENAI_API_KEY set (or use --demo for no API key)
#   - Playwright chromium installed (playwright install chromium)
#
# Usage:
#   ./examples/browser_run.sh
#   ./examples/browser_run.sh --demo

set -euo pipefail

TARGET="https://docs.github.com"
TASK="Find how to create a new repository and locate the quickstart guide"
BACKEND="openai"
EXTRA_ARGS=("$@")

echo "==> Running browser evaluation"
echo "    Target: ${TARGET}"
echo "    Task:   ${TASK}"
echo ""

agentux run "${TARGET}" \
  --surface browser \
  --task "${TASK}" \
  --backend "${BACKEND}" \
  --max-steps 20 \
  "${EXTRA_ARGS[@]}"

echo ""
echo "==> Done. Use 'agentux tui' to browse results interactively."
