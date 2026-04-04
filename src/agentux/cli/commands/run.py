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
    task: str = typer.Option(..., "--task", "-t", help="Task description for the agent"),
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
    if model:
        config.backend.model = model
    if demo:
        config.demo_mode = True
        backend = "mock"
    config.ensure_dirs()

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
    if not demo and backend in ("openai", ""):
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
    console.print()
    print_scorecard(trace.scores)

    # Save to database
    try:
        db = Database(config.database_url)
        db.save_run(trace, analysis)
        console.print(f"\n  [dim]Run saved: {trace.run_id}[/]")
    except Exception as e:
        console.print(f"\n  [warning]Could not save run: {e}[/]")

    if analysis.get("all_insights"):
        console.print("\n[bold]Insights:[/]")
        for insight in analysis["all_insights"][:8]:
            console.print(f"  [dim]-[/] {insight}")
