#!/usr/bin/env bash
# Example: Evaluate a CLI tool's agent usability.
#
# AgentUX will run the CLI tool inside a sandbox and measure how
# easily an agent can discover commands, use flags correctly, and
# recover from errors.
#
# Prerequisites:
#   - agentux installed
#   - OPENAI_API_KEY set (or use --demo)
#   - The target CLI tool must be on your PATH
#
# Usage:
#   ./examples/cli_evaluation.sh
#   ./examples/cli_evaluation.sh --demo

set -euo pipefail

TOOL="git"
TASK="Initialize a new repository, create a README file, stage it, and make a first commit"
EXTRA_ARGS=("$@")

echo "==> Evaluating CLI tool: ${TOOL}"
echo "    Task: ${TASK}"
echo ""

agentux cli "${TOOL}" \
  --task "${TASK}" \
  --max-steps 25 \
  "${EXTRA_ARGS[@]}"

echo ""
echo "==> CLI evaluation complete."
