"""Home / dashboard screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.tui.widgets.sparkline import SparklineWidget


class HomeScreen(Screen):
    """Main dashboard showing recent runs, monitors, and alerts."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("n", "new_run", "New Run"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("[bold cyan] Dashboard[/]\n", id="title")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("[bold]Recent Runs[/]")
                    yield DataTable(id="runs-table")

                with Vertical(classes="panel"):
                    yield Static("[bold]Quick Stats[/]")
                    yield Static(id="stats-summary")
                    yield SparklineWidget(id="aes-sparkline")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("[bold]Monitors[/]")
                    yield DataTable(id="monitors-table")

                with Vertical(classes="panel"):
                    yield Static("[bold]Recent Alerts[/]")
                    yield DataTable(id="alerts-table")

        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    def action_refresh(self) -> None:
        self._load_data()

    def action_new_run(self) -> None:
        self.app.push_screen("live_run")

    def _load_data(self) -> None:
        try:
            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)

            # Recent runs
            runs_table = self.query_one("#runs-table", DataTable)
            runs_table.clear(columns=True)
            runs_table.add_columns("ID", "Surface", "Target", "AES", "Status")
            runs = db.list_runs(limit=10)
            for run in runs:
                aes = f"{run['aes_score']:.0f}" if run.get("aes_score") else "-"
                status = "OK" if run.get("success") else "FAIL"
                runs_table.add_row(
                    run["run_id"],
                    run["surface_type"],
                    run["target"][:25],
                    aes,
                    status,
                )

            # Stats
            stats = self.query_one("#stats-summary", Static)
            total_runs = len(runs)
            avg_aes = 0
            if runs:
                scores = [r["aes_score"] for r in runs if r.get("aes_score")]
                avg_aes = sum(scores) / len(scores) if scores else 0
            success_rate = sum(1 for r in runs if r.get("success")) / max(total_runs, 1)
            stats.update(
                f"  Runs: {total_runs}  Avg AES: {avg_aes:.0f}  "
                f"Success: {success_rate:.0%}"
            )

            # Sparkline
            sparkline = self.query_one("#aes-sparkline", SparklineWidget)
            trend = db.get_trend_data(limit=30)
            sparkline.update_values([t["aes_score"] or 0 for t in trend])

            # Monitors
            monitors_table = self.query_one("#monitors-table", DataTable)
            monitors_table.clear(columns=True)
            monitors_table.add_columns("Name", "Surface", "Schedule", "Enabled")
            for m in db.list_monitors():
                monitors_table.add_row(
                    m["name"],
                    m["surface_type"],
                    m["schedule"],
                    "Yes" if m["enabled"] else "No",
                )

            # Alerts
            alerts_table = self.query_one("#alerts-table", DataTable)
            alerts_table.clear(columns=True)
            alerts_table.add_columns("Severity", "Monitor", "Message")
            for a in db.list_alerts(limit=5, unacknowledged_only=True):
                alerts_table.add_row(
                    a["severity"],
                    a["monitor_name"],
                    a["message"][:40],
                )

        except Exception:
            pass
