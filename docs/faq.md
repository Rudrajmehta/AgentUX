# FAQ

## What is AgentUX?

AgentUX is a synthetic observability tool that measures how usable a surface (website, CLI, documentation, MCP server) is for an AI agent. It sends an LLM-backed agent to interact with the target from scratch, records the interaction trace, and computes usability scores.

## What AgentUX is NOT

- It is not a general-purpose testing framework. It measures agent usability, not correctness.
- It is not an agent framework. It evaluates surfaces, not agents.
- It is not a web scraper. It interacts with surfaces the way an agent would, step by step.

## Do I need an API key?

No. Use `--demo` mode to explore the tool with a deterministic mock backend:

```bash
agentux run https://example.com --surface browser --task "Find the heading" --demo
```

For real evaluations, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

## Which LLM backends are supported?

- **OpenAI** (default) -- any model available through the OpenAI API.
- **Anthropic** -- Claude models via the Anthropic API.
- **Mock** -- deterministic, no API key needed, used with `--demo`.

Any OpenAI-compatible API endpoint can also be used by configuring the base URL.

## What surfaces are supported?

| Surface    | Target type        | Example                                |
|------------|--------------------|----------------------------------------|
| `browser`  | URL                | `https://docs.example.com`             |
| `markdown` | File path or URL   | `./README.md`                          |
| `cli`      | Command name       | `git`, `docker`, `kubectl`             |
| `mcp`      | Server command     | `npx -y @modelcontextprotocol/server-filesystem /tmp` |

## How does demo mode work?

Demo mode (`--demo`) replaces the LLM backend with a mock that follows a fixed script. It produces realistic-looking traces and scores without making any API calls. Useful for testing your setup, CI pipelines, and understanding the output format.

## Where is data stored?

By default, run traces and monitor data are stored in a SQLite database at `~/.agentux/data/agentux.db`. This can be configured in `~/.agentux/config.yaml`.

## How much does a run cost in API tokens?

It depends on the model, surface complexity, and step count. A typical browser evaluation with GPT-4.1 runs 10-20 steps at roughly 1,000-3,000 tokens per step. Budget approximately $0.02-0.10 per run.

## Can I evaluate internal or authenticated sites?

Browser evaluations can navigate to any URL that Playwright can reach. For authenticated sites, you would need to configure Playwright cookies or storage state. This is currently a manual setup step.

## How do I add a new surface type?

Implement the `Surface` abstract base class in `surfaces/base.py` and register it in `core/runner.create_surface()`. See the [Architecture](architecture.md) doc for details.

## Can I use AgentUX in CI?

Yes. See the [Monitoring Guide](monitoring.md) for CI integration examples. Use `--fail-on-alert` to fail the CI step when thresholds are breached.
