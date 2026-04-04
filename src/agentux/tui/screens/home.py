"""Home / dashboard panel."""

from __future__ import annotations

import contextlib
import logging

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Static

from agentux.tui.widgets.sparkline import SparklineWidget

logger = logging.getLogger(__name__)


class HomePanel(Static):
    """Main dashboard showing recent runs, monitors, and alerts."""

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan] Dashboard[/]", id="title")
        yield Static(id="stats-summary")
        yield SparklineWidget(id="aes-sparkline")

        with Horizontal():
            with Vertical(classes="panel"):
                yield Static("[bold]Recent Runs[/]")
                yield DataTable(id="runs-table")

            with Vertical(classes="panel"):
                yield Static("[bold]Monitors[/]")
                yield DataTable(id="monitors-table")

        with Vertical(classes="panel"):
            yield Static("[bold]Recent Alerts[/]")
            yield DataTable(id="alerts-table")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        try:
            from agentux.core.config import load_config
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)

            # Recent runs
            runs_table = self.query_one("#runs-table", DataTable)
            runs_table.clear(columns=True)
            runs_table.add_columns("ID", "Surface", "Target", "AES", "Status")
            runs = db.list_runs(limit=10)
            if runs:
                for run in runs:
                    raw_aes = run.get("aes_score")
                    aes = f"{raw_aes:.0f}" if raw_aes and raw_aes > 0 else "-"
                    status = "OK" if run.get("success") else "FAIL"
                    runs_table.add_row(
                        run["run_id"],
                        run["surface_type"],
                        run["target"][:25],
                        aes,
                        status,
                    )
            else:
                runs_table.add_row("-", "-", "No runs yet. Try: agentux run ... --demo", "-", "-")

            # Stats
            stats = self.query_one("#stats-summary", Static)
            total_runs = len(runs)
            if runs:
                scores = [r["aes_score"] for r in runs if r.get("aes_score") and r["aes_score"] > 0]
                avg_aes = sum(scores) / len(scores) if scores else 0
                success_rate = sum(1 for r in runs if r.get("success")) / max(total_runs, 1)
                stats.update(
                    f"  [bold]Runs:[/] {total_runs}  "
                    f"[bold]Avg AES:[/] {avg_aes:.0f}  "
                    f"[bold]Success:[/] {success_rate:.0%}"
                )
            else:
                stats.update("  [dim]No data yet. Run a benchmark to see stats here.[/]")

            # Sparkline
            sparkline = self.query_one("#aes-sparkline", SparklineWidget)
            trend = db.get_trend_data(limit=30)
            sparkline.update_values([t["aes_score"] or 0 for t in trend])

            # Monitors
            monitors_table = self.query_one("#monitors-table", DataTable)
            monitors_table.clear(columns=True)
            monitors_table.add_columns("Name", "Surface", "Schedule", "Enabled")
            monitors = db.list_monitors()
            if monitors:
                for m in monitors:
                    monitors_table.add_row(
                        m["name"][:20],
                        m["surface_type"],
                        m["schedule"],
                        "Yes" if m["enabled"] else "No",
                    )
            else:
                monitors_table.add_row("-", "-", "No monitors configured", "-")

            # Alerts
            alerts_table = self.query_one("#alerts-table", DataTable)
            alerts_table.clear(columns=True)
            alerts_table.add_columns("Severity", "Monitor", "Message")
            alert_list = db.list_alerts(limit=5, unacknowledged_only=True)
            if alert_list:
                for a in alert_list:
                    alerts_table.add_row(
                        a["severity"],
                        a["monitor_name"],
                        a["message"][:40],
                    )
            else:
                alerts_table.add_row("-", "-", "All clear — no active alerts")

        except Exception as e:
            logger.error(f"Failed to load dashboard data: {e}")
            with contextlib.suppress(Exception):
                self.query_one("#stats-summary", Static).update(
                    f"  [red]Error loading data: {e}[/]"
                )
