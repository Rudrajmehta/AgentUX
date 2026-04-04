"""Coverage / affordance view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from agentux.tui.widgets.heatmap import HeatmapWidget


class CoverageScreen(Screen):
    """Shows coverage and affordance analysis for a run."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    def __init__(self, run_id: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._run_id = run_id

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static(f"[bold cyan] Coverage — {self._run_id}[/]\n", id="title")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield HeatmapWidget(id="coverage-heatmap")

                with Vertical(classes="panel"):
                    yield Static("[bold]Affordance Details[/]")
                    yield DataTable(id="affordance-table")

            with Vertical(classes="panel"):
                yield Static("[bold]Insights[/]")
                yield Static(id="coverage-insights")

        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        if not self._run_id:
            return
        try:
            from agentux.core.config import load_config
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)
            trace = db.get_run(self._run_id)
            analysis = db.get_run_analysis(self._run_id)

            if trace:
                # Heatmap
                heatmap = self.query_one("#coverage-heatmap", HeatmapWidget)
                items = [
                    {"name": a.name, "status": a.status.value}
                    for a in trace.affordances
                    if a.kind in ("section", "command", "tool")
                ]
                heatmap.update_items(items[:20])

                # Affordance table
                table = self.query_one("#affordance-table", DataTable)
                table.clear(columns=True)
                table.add_columns("Name", "Kind", "Status", "Relevant")
                for aff in trace.affordances[:30]:
                    table.add_row(
                        aff.name[:25],
                        aff.kind,
                        aff.status.value,
                        "Yes" if aff.relevant else "No",
                    )

            if analysis:
                insights_widget = self.query_one("#coverage-insights", Static)
                all_insights = analysis.get("all_insights", [])
                text = "\n".join(f"  - {i}" for i in all_insights[:10])
                insights_widget.update(text or "[dim]No insights[/]")

        except Exception:
            pass

    def action_go_back(self) -> None:
        self.app.pop_screen()
