"""agentux inspect — inspect a specific run in detail."""

from __future__ import annotations

import json

import typer

from agentux.cli.formatters import print_run_summary, print_scorecard
from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.utils.console import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def inspect_run(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    analysis: bool = typer.Option(False, "--analysis", "-a", help="Show full analysis"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Inspect a specific run in detail."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    trace = db.get_run(run_id)
    if not trace:
        console.print(f"[error]Run '{run_id}' not found.[/]")
        raise typer.Exit(1)

    if json_output:
        console.print_json(trace.model_dump_json())
        return

    print_run_summary(trace)
    console.print()
    print_scorecard(trace.scores)

    # Affordances
    if trace.affordances:
        from rich.table import Table

        console.print("\n[bold cyan]Affordances[/]\n")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name", width=25)
        table.add_column("Kind", width=12)
        table.add_column("Status", width=12)
        table.add_column("Relevant", width=8)

        for aff in trace.affordances[:30]:
            status_style = {
                "discovered": "cyan",
                "interacted": "green",
                "missed": "red",
                "ignored": "dim",
                "ambiguous": "yellow",
            }.get(aff.status.value, "dim")

            table.add_row(
                aff.name[:24],
                aff.kind,
                f"[{status_style}]{aff.status.value}[/]",
                "Yes" if aff.relevant else "No",
            )
        console.print(table)

    # Steps
    if trace.steps:
        console.print(f"\n[bold cyan]Steps ({len(trace.steps)})[/]\n")
        for step in trace.steps:
            icon = "[green]OK[/]" if step.success else "[red]FAIL[/]"
            console.print(
                f"  {step.step_number:2d}. {icon} {step.action_type}: "
                f"{step.action[:40]}  [dim]{step.tokens_used} tok[/]"
            )

    # Analysis
    if analysis:
        run_analysis = db.get_run_analysis(run_id)
        if run_analysis:
            console.print("\n[bold cyan]Analysis[/]\n")
            console.print_json(json.dumps(run_analysis, indent=2, default=str))
