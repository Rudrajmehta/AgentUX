"""agentux trends — view historical trend data."""

from __future__ import annotations

import typer

from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.utils.console import console, score_style

app = typer.Typer()


@app.callback(invoke_without_command=True)
def trends(
    target: str | None = typer.Option(None, "--target", help="Filter by target"),
    monitor: str | None = typer.Option(None, "--monitor", help="Filter by monitor name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show"),
) -> None:
    """View AES trends and historical data."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    data = db.get_trend_data(target=target, monitor_name=monitor, limit=limit)

    if not data:
        console.print("[dim]No trend data available. Run some benchmarks first.[/]")
        return

    from rich.table import Table

    console.print(f"\n[bold cyan]AES Trends[/] ({len(data)} runs)\n")

    # Sparkline — only include runs that actually produced a real score
    scores = [d["aes_score"] or 0 for d in data if d.get("step_count", 0) > 0]
    if scores:
        _print_sparkline(scores)
        console.print()

    # Table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", width=18)
    table.add_column("AES", justify="right", width=6)
    table.add_column("Status", width=8)
    table.add_column("Steps", justify="right", width=6)
    table.add_column("Tokens", justify="right", width=8)

    for d in data:
        aes = d.get("aes_score") or 0
        steps = d.get("step_count", 0)
        # Show "-" for AES when run had no steps (infra failure)
        aes_display = f"[{score_style(aes)}]{aes:.0f}[/]" if steps > 0 and aes > 0 else "[dim]-[/]"
        table.add_row(
            d["started_at"][:16],
            aes_display,
            "[green]OK[/]" if d["success"] else "[red]FAIL[/]",
            str(steps),
            str(d["total_tokens"]),
        )

    console.print(table)

    # Summary stats
    if scores:
        avg = sum(scores) / len(scores)
        high = max(scores)
        low = min(scores)
        console.print(
            f"\n  [dim]Avg:[/] {avg:.0f}  [dim]High:[/] {high:.0f}  [dim]Low:[/] {low:.0f}"
        )

        if len(scores) >= 2:
            delta = scores[-1] - scores[-2]
            direction = "[green]+{:.0f}[/]" if delta >= 0 else "[red]{:.0f}[/]"
            console.print(f"  [dim]Last change:[/] {direction.format(delta)}")


def _print_sparkline(values: list[float]) -> None:
    """Print a simple ASCII sparkline."""
    blocks = " _.-~*"
    if not values:
        return
    mn, mx = min(values), max(values)
    rng = mx - mn or 1
    line = ""
    for v in values:
        idx = int((v - mn) / rng * (len(blocks) - 1))
        line += blocks[idx]
    console.print(f"  [cyan]{line}[/]  [{score_style(values[-1])}]{values[-1]:.0f}[/]")
