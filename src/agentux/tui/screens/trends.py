"""Trends / observability view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from agentux.tui.widgets.sparkline import SparklineWidget


class TrendsScreen(Screen):
    """Historical trends and observability data."""

    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("escape", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("[bold cyan] Trends[/]\n", id="title")

            with Vertical(classes="panel"):
                yield Static("[bold]AES Over Time[/]")
                yield SparklineWidget(id="aes-trend")
                yield Static(id="trend-stats")

            with Vertical(classes="panel"):
                yield Static("[bold]Run History[/]")
                yield DataTable(id="trend-table")

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

            # Table
            table = self.query_one("#trend-table", DataTable)
            table.clear(columns=True)
            table.add_columns("Time", "AES", "Status", "Steps", "Tokens")
            for d in data[-20:]:
                aes = d.get("aes_score") or 0
                table.add_row(
                    d["started_at"][:16],
                    f"{aes:.0f}",
                    "OK" if d["success"] else "FAIL",
                    str(d["step_count"]),
                    str(d["total_tokens"]),
                )
        except Exception:
            pass

    def action_go_back(self) -> None:
        self.app.pop_screen()
