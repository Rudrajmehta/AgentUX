"""agentux run — execute a single benchmark run."""

from __future__ import annotations

import asyncio

import typer
from rich.live import Live

from agentux.cli.formatters import print_run_summary, print_scorecard
from agentux.core.config import load_config
from agentux.core.models import RunTrace, StepRecord, SurfaceType
from agentux.core.runner import RunCallback, Runner, create_backend, create_surface
from agentux.storage.database import Database
from agentux.utils.branding import print_mini_banner
from agentux.utils.console import console

app = typer.Typer()


class CLIRunCallback(RunCallback):
    """Live CLI output during a run."""

    def __init__(self) -> None:
        self._live: Live | None = None

    def on_step_start(self, step_number: int, trace: RunTrace) -> None:
        console.print(
            f"  [dim]Step {step_number}[/] ",
            end="",
        )

    def on_step_complete(self, step: StepRecord, trace: RunTrace) -> None:
        status = "[green]OK[/]" if step.success else "[red]FAIL[/]"
        console.print(
            f"{status} [dim]{step.action_type}[/] {step.action[:40]} "
            f"[dim]({step.tokens_used} tok, {step.latency_ms:.0f}ms)[/]"
        )
        if step.extracted_facts:
            for fact in step.extracted_facts[:2]:
                console.print(f"    [cyan]+[/] {fact[:70]}")
        if step.errors:
            for err in step.errors[:1]:
                console.print(f"    [red]![/] {err[:70]}")

    def on_run_complete(self, trace: RunTrace, analysis: dict) -> None:
        pass

    def on_error(self, error: str, trace: RunTrace) -> None:
        console.print(f"\n  [red]Error:[/] {error}")


@app.callback(invoke_without_command=True)
def run_command(
    target: str = typer.Argument(..., help="Target URL, file path, or command to evaluate"),
    task: str = typer.Option("", "--task", "-t", help="Task description (omit for general audit)"),
    surface: str = typer.Option(
        "browser",
        "--surface",
        "-s",
        help="Surface type: browser, markdown, cli, mcp",
    ),
    backend: str = typer.Option(
        "openai", "--backend", "-b", help="Agent backend: openai, anthropic, mock"
    ),
    model: str = typer.Option("", "--model", "-m", help="Model name override"),
    base_url: str = typer.Option(
        "", "--base-url", help="OpenAI-compatible base URL (Groq, OpenRouter)"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Maximum steps"),
    headless: bool = typer.Option(True, "--headless/--visible", help="Browser headless mode"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend for demo"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Tags for this run"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Run a benchmark evaluation against a target."""
    print_mini_banner()
    console.print()

    from pathlib import Path as _Path

    config = load_config(_Path(config_path) if config_path else None)
    config.verbose = verbose
    config.browser.headless = headless
    # CLI flags override config; empty string means "use config default"
    if model:
        config.backend.model = model
    if base_url:
        config.backend.base_url = base_url
    if backend:
        config.backend.name = backend
    else:
        backend = config.backend.name
    if max_steps > 0:
        config.max_steps = max_steps
    else:
        max_steps = config.max_steps
    if demo:
        config.demo_mode = True
        backend = "mock"
    config.ensure_dirs()

    # Default audit tasks when --task is omitted
    if not task:
        audit_tasks = {
            "browser": (
                "Explore this website as a first-time visitor. "
                "Find: what the product/site does, main navigation structure, "
                "key pages (pricing, docs, contact), and any calls to action. "
                "Report what was easy and hard to find."
            ),
            "markdown": (
                "Read this document and assess its structure. "
                "Find: what it covers, how sections are organized, "
                "key concepts explained, and any setup/install instructions. "
                "Report what was clear and what was missing."
            ),
            "cli": (
                "Explore this CLI tool as a first-time user. "
                "Discover: available commands, subcommands, and key flags. "
                "Try the most common operation. "
                "Report what was discoverable and what was confusing."
            ),
            "mcp": (
                "Discover all available tools on this MCP server. "
                "Understand what each tool does, inspect the most relevant one, "
                "and try to use it. "
                "Report which tools were clear and which were ambiguous."
            ),
        }
        task = audit_tasks.get(surface, audit_tasks["browser"])
        console.print("  [dim]No --task given. Running general audit.[/]\n")

    valid_surfaces = [s.value for s in SurfaceType]
    if surface not in valid_surfaces:
        console.print(
            f"[error]Unknown surface type: '{surface}'[/]\n"
            f"  Valid types: {', '.join(valid_surfaces)}\n"
        )
        raise SystemExit(1)
    surface_type = SurfaceType(surface)
    tags = list(tag) if tag else []

    # Early credential validation — don't launch surfaces just to fail on auth
    # Skip check if base_url is set (user is using Groq/OpenRouter/etc.)
    if not demo and backend in ("openai", "") and not config.backend.base_url:
        import os

        key = config.backend.api_key or os.environ.get("OPENAI_API_KEY", "")
        if not key:
            console.print(
                f"[error]No OpenAI API key found.[/]\n\n"
                f"  Set it:   export OPENAI_API_KEY='sk-...'\n"
                f"  Or demo:  agentux run {target} --task '{task}' [bold]--demo[/]\n"
                f"  Or use:   --backend anthropic\n"
            )
            raise SystemExit(1)
    if not demo and backend == "anthropic":
        import os

        key = config.backend.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            console.print(
                f"[error]No Anthropic API key found.[/]\n\n"
                f"  Set it:   export ANTHROPIC_API_KEY='sk-ant-...'\n"
                f"  Or demo:  agentux run {target} --task '{task}' [bold]--demo[/]\n"
                f"  Or use:   --backend openai\n"
            )
            raise SystemExit(1)

    console.print(f"  [bold]Target:[/]  {target}")
    console.print(f"  [bold]Task:[/]    {task}")
    console.print(f"  [bold]Surface:[/] {surface_type.value}")
    console.print(f"  [bold]Backend:[/] {backend}")
    console.print()

    callback = CLIRunCallback()
    runner = Runner(config, callback=callback)
    surface_adapter = create_surface(surface_type, target, config)
    agent_backend = create_backend(backend, config)

    trace, analysis = asyncio.run(
        runner.run(surface_adapter, agent_backend, task, target, max_steps, tags)
    )

    console.print()
    print_run_summary(trace)

    # Only show scorecard + analysis if the run actually executed steps
    if trace.step_count > 0 and trace.scores.aes.value > 0:
        console.print()
        print_scorecard(trace.scores)

        # LLM-powered analysis (uses the same backend)
        if not demo:
            from agentux.analyzers.llm_analyzer import analyze_trace_with_llm

            console.print("\n  [dim]Analyzing trace...[/]")
            llm_analysis = asyncio.run(analyze_trace_with_llm(trace, config))
        else:
            from agentux.analyzers.llm_analyzer import _fallback_analysis

            llm_analysis = _fallback_analysis(trace)

        # Print the three sections
        if llm_analysis.get("observations"):
            console.print("\n[bold]Observations:[/]")
            for obs in llm_analysis["observations"]:
                console.print(f"  [dim]-[/] {obs}")

        if llm_analysis.get("insights"):
            console.print("\n[bold cyan]Insights:[/]")
            for ins in llm_analysis["insights"]:
                console.print(f"  [cyan]-[/] {ins}")

        if llm_analysis.get("recommendations"):
            console.print("\n[bold yellow]Recommendations:[/]")
            for rec in llm_analysis["recommendations"]:
                console.print(f"  [yellow]-[/] {rec}")

        # Merge LLM analysis into the analysis dict for storage
        analysis["llm_analysis"] = llm_analysis

    # Save to database
    try:
        db = Database(config.database_url)
        db.save_run(trace, analysis)
        console.print(f"\n  [dim]Run saved: {trace.run_id}[/]")
    except Exception as e:
        console.print(f"\n  [warning]Could not save run: {e}[/]")
