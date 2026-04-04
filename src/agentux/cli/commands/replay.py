"""agentux replay — replay a past run step by step."""

from __future__ import annotations

import time

import typer

from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.utils.console import console, score_style

app = typer.Typer()


@app.callback(invoke_without_command=True)
def replay(
    run_id: str = typer.Argument(..., help="Run ID to replay"),
    speed: float = typer.Option(1.0, "--speed", help="Replay speed multiplier"),
    step_mode: bool = typer.Option(False, "--step", help="Step through one at a time"),
) -> None:
    """Replay a past run step by step in the terminal."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    trace = db.get_run(run_id)
    if not trace:
        console.print(f"[error]Run '{run_id}' not found.[/]")
        raise typer.Exit(1)

    from rich.panel import Panel
    from rich.table import Table

    console.print(Panel(
        f"[bold]Replaying run {trace.run_id}[/]\n"
        f"Target: {trace.target}\n"
        f"Task: {trace.task}\n"
        f"Steps: {trace.step_count}",
        title="[cyan]Replay[/]",
        border_style="cyan",
    ))

    for step in trace.steps:
        status_icon = "[green]OK[/]" if step.success else "[red]FAIL[/]"

        step_table = Table(show_header=False, box=None, pad_edge=False)
        step_table.add_column("Key", style="dim", width=14)
        step_table.add_column("Value")

        step_table.add_row("Thought", step.thought_summary)
        step_table.add_row("Action", f"{step.action_type}: {step.action}")
        if step.result:
            step_table.add_row("Result", step.result[:120])
        if step.extracted_facts:
            step_table.add_row("Facts", ", ".join(step.extracted_facts[:3]))
        if step.errors:
            step_table.add_row("Errors", ", ".join(step.errors[:2]))

        console.print(Panel(
            step_table,
            title=f"Step {step.step_number} {status_icon}",
            border_style="blue" if step.success else "red",
            padding=(0, 1),
        ))

        if step_mode:
            typer.prompt("Press Enter to continue", default="", show_default=False)
        else:
            delay = max(0.2, (step.latency_ms / 1000) / speed)
            time.sleep(min(delay, 2.0))

    console.print()
    aes = trace.scores.aes.value
    console.print(
        f"[bold]Final AES:[/] [{score_style(aes)}]{aes:.0f}/100[/] "
        f"{'[green]PASSED[/]' if trace.success else '[red]FAILED[/]'}"
    )
