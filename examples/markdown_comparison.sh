#!/usr/bin/env bash
# Example: Compare agent usability between a markdown doc and its live site.
#
# This reveals whether your README is easier or harder for an agent
# to navigate than the rendered web version.
#
# Prerequisites:
#   - agentux installed
#   - OPENAI_API_KEY set (or use --demo)
#
# Usage:
#   ./examples/markdown_comparison.sh
#   ./examples/markdown_comparison.sh --demo

set -euo pipefail

MARKDOWN_TARGET="./README.md"
BROWSER_TARGET="https://github.com/Rudrajmehta/AgentUX"
TASK="Find the installation instructions and list of supported surfaces"
EXTRA_ARGS=("$@")

echo "==> Comparing markdown vs browser"
echo "    Markdown: ${MARKDOWN_TARGET}"
echo "    Browser:  ${BROWSER_TARGET}"
echo "    Task:     ${TASK}"
echo ""

agentux compare \
  --surface-a markdown \
  --target-a "${MARKDOWN_TARGET}" \
  --surface-b browser \
  --target-b "${BROWSER_TARGET}" \
  --task "${TASK}" \
  "${EXTRA_ARGS[@]}"

echo ""
echo "==> Comparison complete."
