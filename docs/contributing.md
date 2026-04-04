# Contributing

Thank you for considering a contribution to AgentUX.

## Setup

```bash
git clone https://github.com/Rudrajmehta/AgentUX.git
cd AgentUX
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

## Code Style

AgentUX uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
ruff check src/ tests/
ruff format src/ tests/
```

Configuration is in `pyproject.toml`:

- Target version: Python 3.12
- Line length: 100
- Enabled rule sets: E, F, I, N, W, UP, B, SIM

## Type Checking

```bash
mypy
```

Strict mode is enabled. All public APIs must have type annotations.

## Testing

```bash
pytest
pytest --cov=agentux       # with coverage
pytest tests/test_scoring.py -v   # single module
```

Tests use `pytest-asyncio` for async tests. The asyncio mode is set to `auto` in `pyproject.toml`.

### Writing Tests

- Place tests in `tests/` mirroring the `src/agentux/` structure.
- Use the mock backend (`agents/mock.py`) for tests that exercise the runner.
- Avoid network calls in unit tests; mock external services.

## Architecture Conventions

- **Surfaces** implement the `Surface` ABC in `surfaces/base.py`.
- **Agent backends** implement the `AgentBackend` ABC in `agents/base.py`.
- **Analyzers** subclass the base analyzer in `analyzers/base.py`.
- Domain models live in `core/models.py` and use Pydantic.
- Configuration uses `pydantic-settings` via `core/config.py`.
- CLI commands go in `cli/commands/` as separate Typer sub-apps.

## Pull Request Process

1. Fork the repository and create a feature branch.
2. Make your changes with tests.
3. Run the full check suite: `ruff check . && mypy && pytest`.
4. Open a PR against `main` with a clear description of what changed and why.
5. Address review feedback.

## Commit Messages

Use conventional style: `fix:`, `feat:`, `docs:`, `refactor:`, `test:`, `chore:`.

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
