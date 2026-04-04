# Changelog

All notable changes to AgentUX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-01

### Added

- Initial release of AgentUX
- Four first-class surface types: Browser, Markdown, CLI, MCP
- Agent backends: OpenAI-compatible, Anthropic, Mock
- Transparent scoring engine with 7 decomposable metrics
  - Discoverability Score
  - Actionability Score
  - Recovery Score
  - Efficiency Score
  - Documentation Clarity Score
  - Tool Clarity Score (CLI/MCP)
  - Agent Efficacy Score (AES) — weighted composite
- Full CLI with commands: run, compare, cli, mcp, monitor, replay, trends, alerts, inspect, export, doctor, init, tui
- Interactive Textual TUI with:
  - Home dashboard
  - Trends view with sparklines
  - Alerts management
  - Replay mode with keyboard navigation
  - Coverage heatmaps
  - Comparison view
- Continuous monitoring with YAML config and cron scheduling
- Alert generation on AES regressions and threshold breaches
- Optional alert delivery via Slack/Discord webhooks
- SQLite-backed persistent storage
- Analyzer pipeline: affordance, friction, coverage analysis
- Export to JSON, Markdown, CSV
- Step-by-step run replay
- CLI sandboxing for safe command execution
- MCP server connection and tool evaluation
- Browser automation via Playwright
- Markdown document parsing and section analysis
- Install script for macOS/Linux
- GitHub Actions CI/CD
- Comprehensive test suite
- Full documentation
