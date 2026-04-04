#!/usr/bin/env bash
# Example: Evaluate an MCP server's tool discoverability and usability.
#
# AgentUX will connect to the MCP server, discover its tools, and
# attempt to complete a task using them.
#
# Prerequisites:
#   - agentux installed
#   - OPENAI_API_KEY set (or use --demo)
#   - Node.js / npx available (for the example server)
#
# Usage:
#   ./examples/mcp_evaluation.sh
#   ./examples/mcp_evaluation.sh --demo

set -euo pipefail

COMMAND="npx -y @modelcontextprotocol/server-filesystem /tmp"
TASK="List the files in the allowed directory, read one file, and create a new text file"
EXTRA_ARGS=("$@")

echo "==> Evaluating MCP server"
echo "    Command: ${COMMAND}"
echo "    Task:    ${TASK}"
echo ""

agentux mcp \
  --command "${COMMAND}" \
  --task "${TASK}" \
  --max-steps 20 \
  "${EXTRA_ARGS[@]}"

echo ""
echo "==> MCP evaluation complete."
