# AgentUX

**Synthetic observability for agent usability.**

AgentUX is a terminal-native observability and benchmarking platform that measures how understandable and operable a surface is for AI agents. It answers the question: *can an agent actually use your product?*

```
     _                    _   _   ___  __
    / \   __ _  ___ _ __ | |_| | | \ \/ /
   / _ \ / _` |/ _ \ '_ \| __| | | |\  /
  / ___ \ (_| |  __/ | | | |_| |_| |/  \
 /_/   \_\__, |\___|_| |_|\__|\___//_/\_\
         |___/
```

---

## What is AgentUX?

AgentUX is like **Lighthouse for agent readiness** — it evaluates how well your surfaces (websites, docs, CLIs, MCP tools) work for AI agents encountering them for the first time.

It supports four surface types from day one:

| Surface | What it evaluates |
|---------|------------------|
| **Browser** | Websites via Playwright — section discovery, navigation, CTA findability |
| **Markdown** | Markdown docs and llms.txt — structure clarity, concept coverage |
| **CLI** | Command-line tools — command discovery, flag usage, error recovery |
| **MCP** | MCP tool servers — tool discovery, schema clarity, correct usage |

Every run is **stateless** — the agent has zero prior knowledge of the target. This measures true first-run usability.

## Why AgentUX?

- Your docs team just added llms.txt — is it actually better for agents than the rendered site?
- Your CLI shipped a new release — did agent usability regress?
- Your MCP tools have great schemas... but can an agent pick the right one?
- Your product team wants to track agent-friendliness over time
- You need continuous monitoring, not a one-time audit

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/Rudrajmehta/AgentUX/main/scripts/install.sh | bash
```

Or with pip:

```bash
pip install agentux
playwright install chromium  # for browser surface
```

Verify your setup:

```bash
agentux doctor
```

## Quick Start

### Browser evaluation

```bash
agentux run https://example.com --task "find pricing and enterprise contact" --demo
```

### Markdown comparison

```bash
agentux compare https://example.com \
  --markdown https://example.com/llms.txt \
  --task "understand setup instructions" \
  --demo
```

### CLI evaluation

```bash
agentux cli uv --task "create a new project and add a dependency" --demo
```

### MCP evaluation

```bash
agentux mcp --command "python server.py" --task "discover and use the search tool" --demo
```

> Use `--demo` to run with the mock backend (no API keys needed). Replace with `--backend openai` or `--backend anthropic` for real evaluations.

## Scoring

AgentUX produces transparent, decomposable scores:

| Metric | What it measures |
|--------|-----------------|
| **Discoverability** | Can the agent find relevant sections/commands/tools? |
| **Actionability** | Can discovered affordances be used correctly? |
| **Recovery** | Can the agent recover from errors and dead ends? |
| **Efficiency** | How much wasted effort was there? |
| **Documentation Clarity** | Is the information clear and well-structured? |
| **Tool Clarity** | Are CLI commands and MCP tools self-documenting? |
| **AES** | Agent Efficacy Score — weighted composite of all metrics |

Every score includes its inputs, formula, and explanation. No black boxes.

## Terminal UI

Launch the interactive TUI dashboard:

```bash
agentux tui
```

The TUI provides:
- **Home** — recent runs, monitors, alerts, trend sparklines
- **Trends** — AES over time, regressions, token/latency tracking
- **Alerts** — regression alerts with acknowledge workflow
- **Replay** — step-by-step run playback with keyboard navigation
- **Coverage** — section/command/tool heatmaps
- **Comparison** — side-by-side score deltas

## Continuous Monitoring

Define monitors in YAML:

```yaml
name: pricing-monitor
surface: browser
target: https://example.com
task: find pricing and enterprise contact
schedule: "0 */6 * * *"
backend: openai
model: gpt-4.1
thresholds:
  aes_drop_pct: 10
  success_rate_min: 0.8
  max_steps: 12
```

```bash
agentux monitor add monitors/pricing-monitor.yaml
agentux monitor list
agentux monitor run pricing-monitor
```

Alerts fire on AES regressions, task failures, and threshold breaches. Optional delivery via Slack/Discord webhooks.

## CLI Reference

| Command | Description |
|---------|-------------|
| `agentux run` | Run a single benchmark evaluation |
| `agentux compare` | Compare two surfaces on the same task |
| `agentux cli` | Shortcut for CLI surface evaluation |
| `agentux mcp` | Shortcut for MCP surface evaluation |
| `agentux monitor add/list/run/enable/disable` | Manage monitors |
| `agentux replay <run_id>` | Replay a past run step-by-step |
| `agentux trends` | View AES trends |
| `agentux alerts` | View and manage alerts |
| `agentux inspect <run_id>` | Detailed run inspection |
| `agentux export <run_id>` | Export as JSON/Markdown/CSV |
| `agentux doctor` | Run diagnostics |
| `agentux init` | Initialize config in current directory |
| `agentux tui` | Launch interactive TUI |

## Architecture

```
agentux/
  cli/          CLI commands (Typer)
  tui/          Terminal UI (Textual)
  core/         Models, config, runner
  surfaces/     Surface adapters (Browser, Markdown, CLI, MCP)
  agents/       LLM backends (OpenAI, Anthropic, Mock)
  analyzers/    Affordance, friction, coverage analysis
  scoring/      Transparent metric engine
  storage/      SQLite persistence
  scheduler/    Cron-based monitor scheduling
  replay/       Step-by-step run playback
  export/       JSON, Markdown, CSV export
```

See [docs/architecture.md](docs/architecture.md) for the full design.

## Agent Backend Support

| Backend | Status |
|---------|--------|
| OpenAI-compatible | Supported |
| Anthropic | Supported |
| Mock (demo/test) | Supported |
| Custom harnesses | Extension point (not yet implemented) |

## Configuration

Create `.agentux.yaml` in your project root or use `agentux init`:

```yaml
backend:
  name: openai
  model: gpt-4.1
browser:
  headless: true
cli:
  timeout_seconds: 30
max_steps: 25
```

Environment variables: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

## Export & Integration

```bash
agentux export <run_id> --format json -o report.json
agentux export <run_id> --format markdown -o report.md
agentux export <run_id> --format csv -o steps.csv
```

CI integration:

```yaml
# GitHub Actions
- run: agentux run https://mysite.com --task "find docs" --backend openai
```

## Development

```bash
git clone https://github.com/Rudrajmehta/AgentUX.git
cd AgentUX
make dev
make test
make lint
```

## Contributing

We welcome contributions! See [docs/contributing.md](docs/contributing.md) for guidelines.

1. Fork the repo
2. Create a feature branch
3. Write tests
4. Submit a PR

## License

Apache-2.0. See [LICENSE](LICENSE).

---

Built for teams who care about agent usability.
