"""Shared pytest fixtures for AgentUX tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agentux.core.config import AgentUXConfig, BackendConfig, StorageConfig
from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    Alert,
    MonitorConfig,
    RunStatus,
    RunTrace,
    ScoreCard,
    ScoreResult,
    StepRecord,
    SurfaceType,
)
from agentux.storage.database import Database

# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _make_step(
    number: int,
    action: str = "click",
    action_type: str = "click",
    success: bool = True,
    facts: list[str] | None = None,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    affordances_discovered: list[str] | None = None,
    tokens: int = 300,
    latency: float = 120.0,
    metadata: dict | None = None,
) -> StepRecord:
    return StepRecord(
        step_number=number,
        thought_summary=f"Step {number} reasoning",
        action=action,
        action_type=action_type,
        result=f"Result of step {number}",
        success=success,
        extracted_facts=facts or [],
        affordances_discovered=affordances_discovered or [],
        errors=errors or [],
        warnings=warnings or [],
        tokens_used=tokens,
        latency_ms=latency,
        metadata=metadata or {},
    )


def _make_affordance(
    name: str,
    kind: str = "section",
    status: AffordanceStatus = AffordanceStatus.DISCOVERED,
    relevant: bool = True,
    metadata: dict | None = None,
) -> Affordance:
    return Affordance(
        name=name,
        kind=kind,
        status=status,
        relevant=relevant,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Trace fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_steps() -> list[StepRecord]:
    """A realistic 5-step interaction sequence."""
    return [
        _make_step(
            1,
            action="extract_text",
            action_type="read",
            facts=["Found homepage"],
            affordances_discovered=["nav", "hero"],
        ),
        _make_step(2, action="click Pricing", action_type="click", facts=["Pricing link visible"]),
        _make_step(
            3,
            action="read pricing",
            action_type="read",
            facts=["Free tier", "Pro tier", "Enterprise tier"],
        ),
        _make_step(4, action="click Contact", action_type="click", facts=["Contact form found"]),
        _make_step(5, action="done", action_type="done", facts=["Task complete"]),
    ]


@pytest.fixture
def sample_affordances() -> list[Affordance]:
    """A mixed set of affordances with varied statuses."""
    return [
        _make_affordance("Navigation", status=AffordanceStatus.INTERACTED),
        _make_affordance("Hero Section", status=AffordanceStatus.DISCOVERED),
        _make_affordance("Pricing", status=AffordanceStatus.INTERACTED),
        _make_affordance("Blog", status=AffordanceStatus.MISSED),
        _make_affordance("Footer", kind="link", status=AffordanceStatus.IGNORED, relevant=False),
        _make_affordance("API Docs", status=AffordanceStatus.MISSED),
    ]


@pytest.fixture
def sample_trace(sample_steps: list[StepRecord], sample_affordances: list[Affordance]) -> RunTrace:
    """A completed browser run trace with steps, affordances, and default scores."""
    trace = RunTrace(
        run_id="test_run_001",
        surface_type=SurfaceType.BROWSER,
        target="https://example.com",
        task="Find pricing information and enterprise contact",
        model="gpt-4.1",
        backend="openai",
        status=RunStatus.COMPLETED,
        success=True,
        steps=sample_steps,
        affordances=sample_affordances,
        tags=["test", "browser"],
    )
    trace.total_tokens = sum(s.tokens_used for s in sample_steps)
    trace.total_latency_ms = sum(s.latency_ms for s in sample_steps)
    trace.completed_at = datetime.now(UTC)
    return trace


@pytest.fixture
def empty_trace() -> RunTrace:
    """A trace with no steps and no affordances."""
    return RunTrace(
        run_id="empty_run",
        surface_type=SurfaceType.BROWSER,
        target="https://empty.example.com",
        task="Empty task",
    )


@pytest.fixture
def failed_trace() -> RunTrace:
    """A trace where every step fails."""
    steps = [_make_step(i, success=False, errors=[f"Error at step {i}"]) for i in range(1, 6)]
    trace = RunTrace(
        run_id="failed_run",
        surface_type=SurfaceType.BROWSER,
        target="https://broken.example.com",
        task="Attempt impossible task",
        status=RunStatus.FAILED,
        success=False,
        failure_reason="All steps failed",
        steps=steps,
        affordances=[
            _make_affordance("Nav", status=AffordanceStatus.MISSED),
            _make_affordance("Content", status=AffordanceStatus.MISSED),
        ],
    )
    trace.total_tokens = sum(s.tokens_used for s in steps)
    trace.total_latency_ms = sum(s.latency_ms for s in steps)
    return trace


@pytest.fixture
def cli_trace() -> RunTrace:
    """A CLI surface trace with tool_call / execute steps."""
    steps = [
        _make_step(
            1,
            action="help",
            action_type="read",
            facts=["CLI has init, add, run"],
            affordances_discovered=["init", "add"],
        ),
        _make_step(2, action="init my-project", action_type="execute", facts=["Project created"]),
        _make_step(3, action="add --help", action_type="read", facts=["add takes package name"]),
        _make_step(4, action="add requests", action_type="execute", facts=["Dependency added"]),
        _make_step(5, action="done", action_type="done", facts=["Task complete"]),
    ]
    affordances = [
        _make_affordance("init", kind="command", status=AffordanceStatus.INTERACTED),
        _make_affordance("add", kind="command", status=AffordanceStatus.INTERACTED),
        _make_affordance("remove", kind="command", status=AffordanceStatus.MISSED),
        _make_affordance("--verbose", kind="flag", status=AffordanceStatus.MISSED),
    ]
    trace = RunTrace(
        run_id="cli_run_001",
        surface_type=SurfaceType.CLI,
        target="mypackager",
        task="Create a project and add a dependency",
        model="gpt-4.1",
        backend="openai",
        status=RunStatus.COMPLETED,
        success=True,
        steps=steps,
        affordances=affordances,
    )
    trace.total_tokens = sum(s.tokens_used for s in steps)
    trace.total_latency_ms = sum(s.latency_ms for s in steps)
    trace.completed_at = datetime.now(UTC)
    return trace


@pytest.fixture
def mcp_trace() -> RunTrace:
    """An MCP surface trace with tool_call steps."""
    steps = [
        _make_step(
            1,
            action="list_tools",
            action_type="read",
            facts=["5 tools available"],
            affordances_discovered=["search", "get"],
        ),
        _make_step(
            2, action="inspect_tool search", action_type="read", facts=["search takes query param"]
        ),
        _make_step(
            3, action="call_tool search", action_type="tool_call", facts=["Results returned"]
        ),
        _make_step(4, action="done", action_type="done", facts=["Task complete"]),
    ]
    affordances = [
        _make_affordance("search", kind="tool", status=AffordanceStatus.INTERACTED),
        _make_affordance("get", kind="tool", status=AffordanceStatus.DISCOVERED),
        _make_affordance("create", kind="tool", status=AffordanceStatus.MISSED),
    ]
    trace = RunTrace(
        run_id="mcp_run_001",
        surface_type=SurfaceType.MCP,
        target="test-mcp-server",
        task="Search for test data using MCP tools",
        model="claude-sonnet-4-20250514",
        backend="anthropic",
        status=RunStatus.COMPLETED,
        success=True,
        steps=steps,
        affordances=affordances,
    )
    trace.total_tokens = sum(s.tokens_used for s in steps)
    trace.total_latency_ms = sum(s.latency_ms for s in steps)
    trace.completed_at = datetime.now(UTC)
    return trace


# ---------------------------------------------------------------------------
# ScoreCard fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_scorecard() -> ScoreCard:
    return ScoreCard(
        discoverability=ScoreResult(
            name="Discoverability",
            value=75.0,
            weight=0.25,
            explanation="Found 3/4 relevant affordances",
        ),
        actionability=ScoreResult(
            name="Actionability", value=90.0, weight=0.25, explanation="9/10 actions succeeded"
        ),
        recovery=ScoreResult(
            name="Recovery", value=80.0, weight=0.15, explanation="1 dead end, 1 helpful error"
        ),
        efficiency=ScoreResult(
            name="Efficiency", value=70.0, weight=0.15, explanation="7 steps taken, est optimal 4"
        ),
        documentation_clarity=ScoreResult(
            name="Documentation Clarity", value=85.0, weight=0.20, explanation="Extracted 6 facts"
        ),
        aes=ScoreResult(
            name="Agent Efficacy Score (AES)",
            value=80.5,
            weight=1.0,
            explanation="Weighted composite",
        ),
    )


# ---------------------------------------------------------------------------
# Database fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    """Create a temporary SQLite database."""
    db_path = tmp_path / "test_agentux.db"
    return Database(f"sqlite:///{db_path}")


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_config(tmp_path: Path) -> AgentUXConfig:
    """A config pointing at a temp directory so nothing touches real user data."""
    return AgentUXConfig(
        data_dir=tmp_path / "agentux_test",
        backend=BackendConfig(name="mock", model="mock-model"),
        storage=StorageConfig(database_url=f"sqlite:///{tmp_path / 'test.db'}"),
        max_steps=10,
        demo_mode=True,
    )


# ---------------------------------------------------------------------------
# Monitor / Alert fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_monitor_config() -> MonitorConfig:
    return MonitorConfig(
        name="test-monitor",
        surface=SurfaceType.BROWSER,
        target="https://example.com",
        task="Check pricing page loads",
        schedule="0 */6 * * *",
        backend="mock",
        model="mock-model",
        enabled=True,
    )


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        alert_id="alert_001",
        monitor_name="test-monitor",
        severity="warning",
        message="AES dropped by 15%",
        run_id="test_run_001",
        baseline_run_id="baseline_001",
        metric="aes",
        current_value=65.0,
        threshold_value=80.0,
    )


# ---------------------------------------------------------------------------
# Markdown content fixture
# ---------------------------------------------------------------------------

SAMPLE_MARKDOWN = """\
# Getting Started

Welcome to the project.

## Installation

```bash
pip install example
```

## Configuration

Set the following env vars:

- `API_KEY` - your API key
- `DEBUG` - enable debug mode

## Usage

Run the CLI:

```bash
example run --verbose
```

See [the docs](https://docs.example.com) for more info.

## FAQ

**Q: How do I reset?**
A: Run `example reset`.
"""


@pytest.fixture
def sample_markdown_content() -> str:
    return SAMPLE_MARKDOWN
