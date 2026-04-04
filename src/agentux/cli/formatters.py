"""Rich formatters for CLI output."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agentux.core.models import RunTrace, ScoreCard
from agentux.utils.console import console, format_duration, format_tokens, score_style


def print_scorecard(scores: ScoreCard) -> None:
    """Print a beautiful scorecard panel."""
    table = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Score", justify="right", width=8)
    table.add_column("Explanation", style="dim")

    for _key, result in scores.as_dict().items():
        style = score_style(result.value)
        table.add_row(
            result.name,
            Text(f"{result.value:.0f}", style=style),
            result.explanation[:70],
        )

    panel = Panel(table, title="[bold cyan]Scorecard[/]", border_style="cyan", padding=(1, 2))
    console.print(panel)


def print_run_summary(trace: RunTrace) -> None:
    """Print a run summary panel."""
    status_style = "success" if trace.success else "error"
    status_text = "PASSED" if trace.success else "FAILED"

    info_table = Table(show_header=False, box=None, pad_edge=False)
    info_table.add_column("Key", style="dim", width=16)
    info_table.add_column("Value")

    info_table.add_row("Run ID", trace.run_id)
    info_table.add_row("Surface", trace.surface_type.value)
    info_table.add_row("Target", trace.target[:60])
    info_table.add_row("Task", trace.task[:60])
    info_table.add_row("Model", trace.model or "mock")
    info_table.add_row("Status", Text(status_text, style=status_style))
    info_table.add_row("Steps", str(trace.step_count))
    info_table.add_row("Duration", format_duration(trace.duration_ms))
    info_table.add_row("Tokens", format_tokens(trace.total_tokens))

    aes = trace.scores.aes.value
    if trace.step_count > 0 and aes > 0:
        info_table.add_row(
            "AES",
            Text(f"{aes:.0f}/100", style=score_style(aes)),
        )

    if trace.failure_reason:
        info_table.add_row("Reason", Text(trace.failure_reason[:80], style="error"))

    panel = Panel(
        info_table, title="[bold cyan]Run Summary[/]", border_style="cyan", padding=(1, 2)
    )
    console.print(panel)


def print_comparison(result: Any) -> None:
    """Print a comparison result."""
    table = Table(title="Score Comparison", show_header=True, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("A", justify="right")
    table.add_column("B", justify="right")
    table.add_column("Delta", justify="right")

    scores_a = result.run_a.scores.as_dict()
    scores_b = result.run_b.scores.as_dict()

    for key in scores_a:
        if key in scores_b:
            val_a = scores_a[key].value
            val_b = scores_b[key].value
            delta = val_b - val_a
            delta_style = "green" if delta > 0 else "red" if delta < 0 else "dim"
            delta_text = f"+{delta:.0f}" if delta > 0 else f"{delta:.0f}"
            table.add_row(
                scores_a[key].name,
                f"{val_a:.0f}",
                f"{val_b:.0f}",
                Text(delta_text, style=delta_style),
            )

    console.print(table)

    if result.insights:
        console.print("\n[bold]Insights:[/]")
        for insight in result.insights:
            console.print(f"  [dim]-[/] {insight}")

    if result.winner:
        winner_label = "A" if result.winner == "a" else "B"
        console.print(f"\n[bold green]Winner: {winner_label}[/]")


def print_alerts_table(alerts: list[dict[str, Any]]) -> None:
    """Print alerts in a table."""
    table = Table(title="Alerts", show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=20)
    table.add_column("Severity", width=10)
    table.add_column("Monitor")
    table.add_column("Message")
    table.add_column("Ack", width=5)

    for alert in alerts:
        sev_style = {
            "critical": "bold red",
            "warning": "bold yellow",
            "info": "cyan",
        }.get(alert["severity"], "dim")

        table.add_row(
            alert["created_at"][:19],
            Text(alert["severity"], style=sev_style),
            alert["monitor_name"],
            alert["message"][:50],
            "Yes" if alert["acknowledged"] else "No",
        )

    console.print(table)


def print_runs_table(runs: list[dict[str, Any]]) -> None:
    """Print runs in a table."""
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Run ID", width=14)
    table.add_column("Surface", width=10)
    table.add_column("Target", width=30)
    table.add_column("AES", justify="right", width=6)
    table.add_column("Status", width=8)
    table.add_column("Steps", justify="right", width=6)
    table.add_column("Time", style="dim", width=18)

    for run in runs:
        aes = run.get("aes_score")
        # Don't show AES for failed infra runs (0 or None)
        if aes and aes > 0:
            aes_text = Text(f"{aes:.0f}", style=score_style(aes))
        else:
            aes_text = Text("-", style="dim")
        status_style = "success" if run.get("success") else "error"
        table.add_row(
            run["run_id"],
            run["surface_type"],
            run["target"][:28],
            aes_text,
            Text(run["status"], style=status_style),
            str(run.get("step_count", 0)),
            run["started_at"][:16],
        )

    console.print(table)
