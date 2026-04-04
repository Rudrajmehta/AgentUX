# Quickstart

This guide walks through your first AgentUX evaluation. No API keys are needed if you use `--demo` mode.

## 1. Demo Run

Run a browser evaluation with the mock backend:

```bash
agentux run https://example.com \
  --surface browser \
  --task "Find the main heading and any links on the page" \
  --demo
```

The `--demo` flag uses a deterministic mock agent so you can explore the output format without spending API tokens.

## 2. Browser Evaluation (Live)

Evaluate a real website with an LLM agent:

```bash
export OPENAI_API_KEY="sk-..."

agentux run https://docs.example.com/pricing \
  --surface browser \
  --task "Find the price of the Pro plan and how to start a free trial" \
  --backend openai
```

## 3. Markdown Comparison

Compare how well an agent navigates a markdown doc versus the live site:

```bash
agentux compare \
  --surface-a markdown \
  --target-a ./docs/README.md \
  --surface-b browser \
  --target-b https://example.com/docs \
  --task "Find the installation instructions"
```

## 4. CLI Evaluation

Evaluate a CLI tool's usability for an agent:

```bash
agentux cli git \
  --task "Initialize a new repo, create a file, and make a first commit"
```

## 5. MCP Evaluation

Evaluate an MCP server's tool discoverability:

```bash
agentux mcp \
  --command "npx -y @modelcontextprotocol/server-filesystem /tmp" \
  --task "List files in the allowed directory and read one of them"
```

## 6. Viewing Results

After any run, AgentUX prints a scorecard to the terminal:

```
Run abc123f4 completed (12 steps, 3.4s)

  Discoverability   82  ████████░░
  Actionability     91  █████████░
  Recovery          70  ███████░░░
  Efficiency        65  ██████░░░░
  Doc Clarity       78  ███████░░░
  ─────────────────────────────────
  AES               77  ███████░░░
```

Inspect a run in detail:

```bash
agentux inspect <run-id>
```

Export results:

```bash
agentux export <run-id> --format json
agentux export <run-id> --format csv
agentux export <run-id> --format markdown
```

## 7. Interactive TUI

Launch the full terminal dashboard for browsing runs, viewing trends, and replaying traces:

```bash
agentux tui
```

The TUI includes screens for: home overview, live run monitoring, comparison view, coverage heatmaps, trend charts, alert management, and step-by-step replay.

## Next Steps

- [Scoring Reference](scoring.md) -- understand what each metric measures.
- [Monitoring Guide](monitoring.md) -- set up recurring monitors with alerts.
- [Architecture](architecture.md) -- understand the internals.
