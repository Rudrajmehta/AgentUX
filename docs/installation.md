# Installation

## Prerequisites

- **Python 3.12+** (3.13 also supported)
- **Playwright** (for browser evaluations only)

## Quick Install

Install from GitHub:

```bash
pip install git+https://github.com/Rudrajmehta/AgentUX.git
```

Or use the install script, which checks prerequisites and installs Playwright:

```bash
curl -fsSL https://raw.githubusercontent.com/Rudrajmehta/AgentUX/main/scripts/install.sh | bash
```

## Post-Install

Install Playwright browsers (required only for browser surface evaluations):

```bash
playwright install chromium
```

## Environment Variables

AgentUX needs an LLM API key to drive evaluations. Set at least one:

| Variable            | Required for        | Example                  |
|---------------------|---------------------|--------------------------|
| `OPENAI_API_KEY`    | OpenAI backend      | `sk-...`                 |
| `ANTHROPIC_API_KEY` | Anthropic backend   | `sk-ant-...`             |

You can skip API keys entirely by using `--demo` mode, which uses a deterministic mock backend.

## Verify Installation

Run the built-in diagnostics:

```bash
agentux doctor
```

This checks Python version, installed dependencies, Playwright browser availability, API key presence, and database connectivity.

## Developer Setup

Clone the repository and use the dev setup script:

```bash
git clone https://github.com/Rudrajmehta/AgentUX.git
cd AgentUX
./scripts/dev-setup.sh
```

Or manually:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
pytest
```

## Upgrading

```bash
pip install --upgrade git+https://github.com/Rudrajmehta/AgentUX.git
```
