# Architecture Overview

AgentUX is a synthetic observability tool that evaluates how usable a surface (website, CLI tool, documentation, MCP server) is for an AI agent encountering it for the first time. It does this by dispatching an LLM-backed agent against the target, recording a detailed interaction trace, and scoring the result.

## Module Map

```
src/agentux/
  core/          Domain models, runner orchestrator, config, exceptions
  surfaces/      Adapters for each surface type (browser, markdown, CLI, MCP)
  agents/        LLM backend abstraction (OpenAI, Anthropic, mock)
  analyzers/     Post-run analysis pipeline (affordance, coverage, friction)
  scoring/       Metric definitions and computation engine
  storage/       SQLAlchemy-backed persistence (SQLite by default)
  scheduler/     APScheduler-based recurring monitors and alert delivery
  tui/           Textual-based interactive dashboard
  cli/           Typer-based command-line interface
  export/        Output formatters (JSON, CSV, Markdown)
  replay/        Step-by-step trace replay
  utils/         Console helpers, branding, CLI sandboxing
```

## Data Flow

```
                  CLI / TUI
                     |
                     v
              +-------------+
              |   Runner    |  Orchestrates a single evaluation run
              +------+------+
                     |
         +-----------+-----------+
         |                       |
    +----v----+           +------v------+
    | Surface |           | AgentBackend|
    +---------+           +-------------+
    browser, md,          openai,
    cli, mcp              anthropic, mock
         |                       |
         +-----------+-----------+
                     |
                     v
              +-----------+         +----------+
              |  RunTrace |-------->| Analyzers|
              +-----------+         +----+-----+
                     |                   |
                     v                   v
              +-------------+     +-----------+
              |ScoringEngine|     | Analysis  |
              +------+------+     +-----+-----+
                     |                  |
                     v                  v
              +-----------+       +---------+
              |  Storage  |       | Export  |
              +-----------+       +---------+
                     |
                     v
              +-------------+
              |  Scheduler  |  Recurring monitors, alerts
              +-------------+
```

## Key Abstractions

### Surface Adapter Pattern

Every evaluatable target is wrapped in a `Surface` implementation (`surfaces/base.py`). The interface exposes five operations:

| Method            | Purpose                                        |
|-------------------|-------------------------------------------------|
| `setup()`         | Initialize the surface (launch browser, etc.)   |
| `teardown()`      | Release resources                               |
| `discover()`      | Return a list of affordances found on the surface|
| `act(action, params)` | Perform an action and return the result     |
| `observe()`       | Return a text snapshot of the current state      |

Concrete adapters: `BrowserSurface` (Playwright), `MarkdownSurface` (markdown-it), `CLISurface` (subprocess in sandbox), `MCPSurface` (stdio/SSE client).

### Agent Backend Abstraction

The `AgentBackend` base class (`agents/base.py`) defines a single `decide()` method. Given the current observation, task, and history, it returns an `AgentDecision` containing the next action, extracted facts, and uncertainty level. Backends exist for OpenAI, Anthropic, and a deterministic mock used in demo mode.

Future harness integrations (LangChain, CrewAI, custom agent frameworks) should implement `AgentBackend` to plug into the evaluation loop without modifying the runner.

### Trace Model

A `RunTrace` (`core/models.py`) captures everything about a single evaluation:

- **StepRecord** -- per-step action, result, success flag, extracted facts, latency, token count, and metadata (including uncertainty).
- **Affordance** -- a discoverable element on the surface (link, command, tool, section) with a status: discovered, interacted, missed, ignored, or ambiguous.
- **ScoreCard** -- the computed scores for the run.

Traces are immutable after completion and can be serialized, exported, replayed, and compared.

### Analyzer Pipeline

The `AnalyzerPipeline` (`analyzers/pipeline.py`) runs a chain of analyzers over a completed trace:

1. **AffordanceAnalyzer** -- classifies affordance statuses and gaps.
2. **CoverageAnalyzer** -- measures what fraction of the surface was explored.
3. **FrictionAnalyzer** -- detects friction points (dead ends, backtracks, repeated failures).

Each analyzer produces a dict of findings that are merged into the final analysis output.

### Scoring Engine

The `ScoringEngine` (`scoring/engine.py`) computes six component metrics plus a composite AES score. Metric definitions live in `scoring/definitions.py`; computation functions live in `scoring/metrics.py`. The engine is surface-aware: browser and markdown runs omit Tool Clarity, while CLI and MCP runs include it. See the [Scoring Reference](scoring.md) for details.

### Storage Layer

`storage/database.py` wraps SQLAlchemy with a SQLite backend (by default stored in `~/.agentux/data/agentux.db`). It persists run traces, trend data, monitor configs, and alerts. The schema is defined in `storage/models.py`.

### Scheduler and Alerts

The `scheduler/` module uses APScheduler to run monitors on cron schedules. After each monitored run, `scheduler/alerts.py` checks results against thresholds and delivers alerts via Slack or Discord webhooks.

## Extension Points

- **New surface types.** Implement the `Surface` ABC and register it in `core/runner.create_surface()`.
- **New agent backends / harness integrations.** Implement the `AgentBackend` ABC. This is the intended integration point for external agent frameworks.
- **New analyzers.** Subclass `analyzers/base.py` and add to the pipeline.
- **New export formats.** Add a module under `export/`.
- **Alert channels.** Extend `scheduler/alerts.deliver_alert()`.
