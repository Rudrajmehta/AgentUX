"""agentux alerts — view and manage alerts."""

from __future__ import annotations

import typer

from agentux.cli.formatters import print_alerts_table
from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.utils.console import console

app = typer.Typer(help="View and manage alerts.")


@app.callback(invoke_without_command=True)
def alerts_list(
    limit: int = typer.Option(20, "--limit", "-n"),
    all_alerts: bool = typer.Option(False, "--all", help="Include acknowledged alerts"),
) -> None:
    """List recent alerts."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    alert_list = db.list_alerts(limit=limit, unacknowledged_only=not all_alerts)
    if not alert_list:
        console.print("[dim]No alerts. All clear.[/]")
        return

    print_alerts_table(alert_list)


@app.command("ack")
def alerts_ack(
    alert_id: str = typer.Argument(..., help="Alert ID to acknowledge"),
) -> None:
    """Acknowledge an alert."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    db.acknowledge_alert(alert_id)
    console.print(f"[success]Alert {alert_id} acknowledged.[/]")
