"""Trends / observability panel."""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import DataTable, Static

from agentux.tui.widgets.sparkline import SparklineWidget

logger = logging.getLogger(__name__)


class TrendsPanel(Static):
    """Historical trends and observability data."""

    def compose(self) -> ComposeResult:
        yield Static("[bold cyan] Trends[/]", id="title")

        with Vertical(classes="panel"):
            yield Static("[bold]AES Over Time[/]")
            yield SparklineWidget(id="aes-trend")
            yield Static(id="trend-stats")

        with Vertical(classes="panel"):
            yield Static("[bold]Run History[/]")
            yield DataTable(id="trend-table")

    def on_mount(self) -> None:
        self.load_data()

    def load_data(self) -> None:
        try:
            from agentux.core.config import load_config
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)

            data = db.get_trend_data(limit=50)

            # Sparkline
            scores = [d["aes_score"] or 0 for d in data]
            sparkline = self.query_one("#aes-trend", SparklineWidget)
            sparkline.update_values(scores)

            # Stats
            stats = self.query_one("#trend-stats", Static)
            if scores:
                avg = sum(scores) / len(scores)
                stats.update(
                    f"  Avg: {avg:.0f}  High: {max(scores):.0f}  "
                    f"Low: {min(scores):.0f}  Runs: {len(scores)}"
                )
            else:
                stats.update("  [dim]No trend data yet.[/]")

            # Table
            table = self.query_one("#trend-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Time", "AES", "Status", "Steps", "Tokens")
            if data:
                for d in data[-20:]:
                    aes = d.get("aes_score") or 0
                    table.add_row(
                        d["started_at"][:16],
                        f"{aes:.0f}",
                        "OK" if d["success"] else "FAIL",
                        str(d["step_count"]),
                        str(d["total_tokens"]),
                    )
            else:
                table.add_row("-", "-", "No runs yet", "-", "-")

        except Exception as e:
            logger.error(f"Failed to load trend data: {e}")
