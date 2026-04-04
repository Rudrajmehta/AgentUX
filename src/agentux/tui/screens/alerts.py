"""Alerts view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class AlertsScreen(Screen):
    """View and manage alerts."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("a", "ack_selected", "Acknowledge"),
        ("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("[bold cyan] Alerts[/]\n", id="title")

            with Vertical(classes="panel"):
                yield DataTable(id="alerts-table", cursor_type="row")

        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    def action_refresh(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
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
            for a in alerts:
                table.add_row(
                    a["alert_id"],
                    a["severity"],
                    a["monitor_name"],
                    a["message"][:40],
                    a["created_at"][:16],
                    "Yes" if a["acknowledged"] else "No",
                )
        except Exception:
            pass

    def action_ack_selected(self) -> None:
        table = self.query_one("#alerts-table", DataTable)
        if table.cursor_row is not None:
            try:
                row = table.get_row_at(table.cursor_row)
                alert_id = str(row[0])
                from agentux.core.config import load_config
                from agentux.storage.database import Database

                config = load_config()
                config.ensure_dirs()
                db = Database(config.database_url)
                db.acknowledge_alert(alert_id)
                self._load_data()
            except Exception:
                pass

    def action_go_back(self) -> None:
        self.app.pop_screen()
