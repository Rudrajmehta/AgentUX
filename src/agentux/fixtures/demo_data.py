"""Demo data generator for seeding the database with realistic sample traces."""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
    StepRecord,
    SurfaceType,
)
from agentux.scoring.engine import ScoringEngine


def _ts(days_ago: int = 0, hours_ago: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(days=days_ago, hours=hours_ago)


def generate_browser_trace(target: str = "https://example.com", days_ago: int = 0) -> RunTrace:
    """Generate a realistic browser surface trace."""
    trace = RunTrace(
        surface_type=SurfaceType.BROWSER,
        target=target,
        task="Find pricing information and enterprise contact",
        model="gpt-4.1",
        backend="openai",
        started_at=_ts(days_ago),
        tags=["demo", "browser"],
    )

    sections = [
        ("header", True),
        ("navigation", True),
        ("hero", True),
        ("features", True),
        ("pricing", True),
        ("docs", False),
        ("footer", False),
        ("search", False),
        ("cta", True),
        ("login", False),
    ]

    for name, relevant in sections:
        status = random.choice(
            [AffordanceStatus.DISCOVERED, AffordanceStatus.INTERACTED, AffordanceStatus.MISSED]
        )
        if name in ("pricing", "cta", "navigation"):
            status = AffordanceStatus.INTERACTED
        trace.affordances.append(
            Affordance(
                name=name,
                kind="section",
                status=status,
                relevant=relevant,
            )
        )

    steps_data = [
        (
            "Observing the homepage structure",
            "extract_text",
            "read",
            True,
            ["Product homepage with nav, hero, features"],
        ),
        (
            "Found navigation — looking for pricing link",
            "click",
            "click",
            True,
            ["Nav has: Home, Features, Pricing, Docs, Contact"],
        ),
        ("Navigated to pricing page", "navigate", "navigate", True, ["Pricing page loaded"]),
        (
            "Reading pricing tiers",
            "extract_text",
            "read",
            True,
            ["Three tiers: Free, Pro ($29/mo), Enterprise (custom)"],
        ),
        ("Looking for enterprise contact", "click", "click", True, ["Contact Sales button found"]),
        (
            "Task complete",
            "done",
            "done",
            True,
            ["Pricing: Free/Pro/Enterprise", "Contact: sales@example.com"],
        ),
    ]

    for i, (thought, action, atype, success, facts) in enumerate(steps_data, 1):
        trace.add_step(
            StepRecord(
                step_number=i,
                thought_summary=thought,
                action=action,
                action_type=atype,
                result=f"Step {i} result",
                success=success,
                extracted_facts=facts,
                tokens_used=random.randint(200, 600),
                latency_ms=random.uniform(500, 2000),
                metadata={"uncertainty": random.uniform(0.05, 0.3)},
            )
        )

    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def generate_markdown_trace(
    target: str = "https://example.com/llms.txt", days_ago: int = 0
) -> RunTrace:
    """Generate a realistic markdown surface trace."""
    trace = RunTrace(
        surface_type=SurfaceType.MARKDOWN,
        target=target,
        task="Understand setup instructions",
        model="gpt-4.1",
        backend="openai",
        started_at=_ts(days_ago),
        tags=["demo", "markdown"],
    )

    for name in [
        "Introduction",
        "Installation",
        "Configuration",
        "Quick Start",
        "API Reference",
        "FAQ",
    ]:
        status = random.choice([AffordanceStatus.INTERACTED, AffordanceStatus.DISCOVERED])
        trace.affordances.append(
            Affordance(name=name, kind="section", status=status, relevant=True)
        )

    steps_data = [
        ("Listing document sections", "list_sections", "read", True, ["6 sections found"]),
        ("Searching for setup info", "search", "search", True, ["Setup section found"]),
        (
            "Reading Installation section",
            "read_section",
            "read",
            True,
            ["pip install example-tool"],
        ),
        (
            "Reading Quick Start section",
            "read_section",
            "read",
            True,
            ["3-step quickstart provided"],
        ),
        ("Task complete", "done", "done", True, ["Setup: install, configure, run"]),
    ]

    for i, (thought, action, atype, success, facts) in enumerate(steps_data, 1):
        trace.add_step(
            StepRecord(
                step_number=i,
                thought_summary=thought,
                action=action,
                action_type=atype,
                result=f"Step {i} result",
                success=success,
                extracted_facts=facts,
                tokens_used=random.randint(150, 400),
                latency_ms=random.uniform(300, 1000),
                metadata={"uncertainty": random.uniform(0.05, 0.2)},
            )
        )

    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def generate_cli_trace(target: str = "uv", days_ago: int = 0) -> RunTrace:
    """Generate a realistic CLI surface trace."""
    trace = RunTrace(
        surface_type=SurfaceType.CLI,
        target=target,
        task="Create a new project and add a dependency",
        model="gpt-4.1",
        backend="openai",
        started_at=_ts(days_ago),
        tags=["demo", "cli"],
    )

    for name in ["init", "add", "remove", "run", "sync", "lock"]:
        status = (
            AffordanceStatus.INTERACTED if name in ("init", "add") else AffordanceStatus.DISCOVERED
        )
        trace.affordances.append(
            Affordance(name=name, kind="command", status=status, relevant=name in ("init", "add"))
        )

    for flag in ["--help", "--version", "--name", "--python"]:
        trace.affordances.append(
            Affordance(name=flag, kind="flag", status=AffordanceStatus.DISCOVERED, relevant=True)
        )

    steps_data = [
        (
            "Checking help to discover commands",
            "help",
            "read",
            True,
            ["Commands: init, add, remove, run, sync"],
        ),
        ("Creating new project", "execute", "execute", True, ["Project initialized"]),
        ("Checking add help", "help", "read", True, ["add takes package name"]),
        ("Adding dependency", "execute", "execute", True, ["requests added"]),
        ("Task complete", "done", "done", True, ["Project created with dependency"]),
    ]

    for i, (thought, action, atype, success, facts) in enumerate(steps_data, 1):
        trace.add_step(
            StepRecord(
                step_number=i,
                thought_summary=thought,
                action=action,
                action_type=atype,
                result=f"Step {i} result",
                success=success,
                extracted_facts=facts,
                tokens_used=random.randint(150, 500),
                latency_ms=random.uniform(200, 800),
                metadata={"uncertainty": random.uniform(0.05, 0.25)},
            )
        )

    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def generate_mcp_trace(target: str = "python server.py", days_ago: int = 0) -> RunTrace:
    """Generate a realistic MCP surface trace."""
    trace = RunTrace(
        surface_type=SurfaceType.MCP,
        target=target,
        task="Discover the search tool and use it",
        model="gpt-4.1",
        backend="openai",
        started_at=_ts(days_ago),
        tags=["demo", "mcp"],
    )

    for name, desc in [
        ("search", "Search documents"),
        ("create", "Create record"),
        ("delete", "Delete record"),
        ("list", "List records"),
    ]:
        status = AffordanceStatus.INTERACTED if name == "search" else AffordanceStatus.DISCOVERED
        trace.affordances.append(
            Affordance(
                name=name,
                kind="tool",
                status=status,
                relevant=name == "search",
                notes=desc,
            )
        )

    steps_data = [
        ("Listing available tools", "list_tools", "read", True, ["4 tools available"]),
        (
            "Inspecting search tool schema",
            "inspect_tool",
            "read",
            True,
            ["search takes query param"],
        ),
        ("Calling search tool", "call_tool", "tool_call", True, ["Results returned"]),
        ("Task complete", "done", "done", True, ["Found and used search tool correctly"]),
    ]

    for i, (thought, action, atype, success, facts) in enumerate(steps_data, 1):
        trace.add_step(
            StepRecord(
                step_number=i,
                thought_summary=thought,
                action=action,
                action_type=atype,
                result=f"Step {i} result",
                success=success,
                extracted_facts=facts,
                tokens_used=random.randint(150, 400),
                latency_ms=random.uniform(200, 600),
                metadata={"uncertainty": random.uniform(0.05, 0.2)},
            )
        )

    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def seed_database(db_url: str) -> None:
    """Seed a database with demo data for all surface types."""
    from agentux.analyzers.pipeline import AnalyzerPipeline
    from agentux.storage.database import Database

    db = Database(db_url)
    pipeline = AnalyzerPipeline()

    generators = [
        generate_browser_trace,
        generate_markdown_trace,
        generate_cli_trace,
        generate_mcp_trace,
    ]

    for days_ago in range(7, -1, -1):
        for gen in generators:
            trace = gen(days_ago=days_ago)
            analysis = pipeline.analyze(trace)
            db.save_run(trace, analysis)
