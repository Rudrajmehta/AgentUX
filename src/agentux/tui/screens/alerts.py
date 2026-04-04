"""Alerts panel."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

logger = logging.getLogger(__name__)


class AlertsPanel(Static):
    """View and manage alerts."""

    BINDINGS = [
        ("a", "ack_selected", "Acknowledge"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan] Alerts[/]", id="title")

        with Vertical(classes="panel"):
            yield Static(
                "[dim]Press [bold]a[/] to acknowledge selected alert | [bold]r[/] to refresh[/]"
            )
            yield DataTable(id="alerts-table", cursor_type="row")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        try:
            from agentux.core.config import load_config
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)

            table = self.query_one("#alerts-table", DataTable)
            table.clear(columns=True)
            table.add_columns("ID", "Severity", "Monitor", "Message", "Time", "Ack")

            alerts = db.list_alerts(limit=50)
            if alerts:
                for a in alerts:
                    table.add_row(
                        a["alert_id"],
                        a["severity"],
                        a["monitor_name"],
                        a["message"][:40],
                        a["created_at"][:16],
                        "Yes" if a["acknowledged"] else "No",
                    )
            else:
                table.add_row("-", "-", "-", "No alerts — all clear", "-", "-")

        except Exception as e:
            logger.error(f"Failed to load alerts: {e}")

    def action_ack_selected(self) -> None:
        table = self.query_one("#alerts-table", DataTable)
        if table.cursor_row is not None:
            try:
                row = table.get_row_at(table.cursor_row)
                alert_id = str(row[0])
                if alert_id == "-":
                    return
                from agentux.core.config import load_config
                from agentux.storage.database import Database

                config = load_config()
                config.ensure_dirs()
                db = Database(config.database_url)
                db.acknowledge_alert(alert_id)
                self.load_data()
            except Exception as e:
                logger.error(f"Failed to acknowledge alert: {e}")
