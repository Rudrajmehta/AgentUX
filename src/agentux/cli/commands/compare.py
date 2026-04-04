"""agentux compare — compare two surfaces on the same task."""

from __future__ import annotations

import asyncio
from typing import Optional

import typer

from agentux.cli.formatters import print_comparison, print_run_summary, print_scorecard
from agentux.core.config import load_config
from agentux.core.models import SurfaceType
from agentux.core.runner import Runner, create_backend, create_surface
from agentux.core.trace import compare_traces
from agentux.storage.database import Database
from agentux.utils.branding import print_mini_banner
from agentux.utils.console import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def compare_command(
    target_a: str = typer.Argument(..., help="First target (URL, path, or command)"),
    task: str = typer.Option(..., "--task", "-t", help="Task for both targets"),
    target_b: str = typer.Option("", "--markdown", "--vs", "-B", help="Second target to compare against"),
    surface_a: str = typer.Option("browser", "--surface-a", "-sa", help="Surface type for target A"),
    surface_b: str = typer.Option("markdown", "--surface-b", "-sb", help="Surface type for target B"),
    backend: str = typer.Option("openai", "--backend", "-b", help="Agent backend"),
    model: str = typer.Option("", "--model", "-m", help="Model override"),
    max_steps: int = typer.Option(25, "--max-steps", help="Max steps per run"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend"),
    config_path: Optional[str] = typer.Option(None, "--config", "-c", help="Config file"),
) -> None:
    """Compare agent usability between two targets."""
    if not target_b:
        console.print("[error]Provide a second target with --vs or --markdown[/]")
        raise typer.Exit(1)

    print_mini_banner()
    console.print()

    config = load_config(config_path and __import__("pathlib").Path(config_path))
    if model:
        config.backend.model = model
    if demo:
        config.demo_mode = True
        backend = "mock"
    config.ensure_dirs()

    console.print(f"  [bold]A:[/] {target_a} ({surface_a})")
    console.print(f"  [bold]B:[/] {target_b} ({surface_b})")
    console.print(f"  [bold]Task:[/] {task}")
    console.print()

    runner = Runner(config)

    async def run_both():
        # Run A
        console.print("[bold cyan]Running A...[/]")
        surface_obj_a = create_surface(SurfaceType(surface_a), target_a, config)
        backend_obj_a = create_backend(backend, config)
        trace_a, analysis_a = await runner.run(
            surface_obj_a, backend_obj_a, task, target_a, max_steps, tags=["compare-a"]
        )

        # Run B
        console.print("\n[bold cyan]Running B...[/]")
        surface_obj_b = create_surface(SurfaceType(surface_b), target_b, config)
        backend_obj_b = create_backend(backend, config)
        trace_b, analysis_b = await runner.run(
            surface_obj_b, backend_obj_b, task, target_b, max_steps, tags=["compare-b"]
        )

        return trace_a, analysis_a, trace_b, analysis_b

    trace_a, analysis_a, trace_b, analysis_b = asyncio.run(run_both())

    console.print("\n[bold cyan]Results — A[/]")
    print_run_summary(trace_a)
    print_scorecard(trace_a.scores)

    console.print("\n[bold cyan]Results — B[/]")
    print_run_summary(trace_b)
    print_scorecard(trace_b.scores)

    comparison = compare_traces(trace_a, trace_b)
    console.print()
    print_comparison(comparison)

    # Save
    try:
        db = Database(config.database_url)
        db.save_run(trace_a, analysis_a)
        db.save_run(trace_b, analysis_b)
    except Exception:
        pass
