"""Comparison view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from agentux.tui.widgets.scorecard import ScoreCardWidget


class ComparisonScreen(Screen):
    """Side-by-side comparison of two runs."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, run_id_a: str = "", run_id_b: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._run_id_a = run_id_a
        self._run_id_b = run_id_b

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("[bold cyan] Comparison[/]\n", id="title")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("[bold]Run A[/]")
                    yield Static(id="info-a")
                    yield ScoreCardWidget(id="scores-a")

                with Vertical(classes="panel"):
                    yield Static("[bold]Run B[/]")
                    yield Static(id="info-b")
                    yield ScoreCardWidget(id="scores-b")

            with Vertical(classes="panel"):
                yield Static("[bold]Score Deltas[/]")
                yield DataTable(id="deltas-table")

            with Vertical(classes="panel"):
                yield Static("[bold]Insights[/]")
                yield Static(id="comparison-insights")

        yield Footer()

    def on_mount(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        if not self._run_id_a or not self._run_id_b:
            return

        try:
            from agentux.core.config import load_config
            from agentux.core.trace import compare_traces
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)

            trace_a = db.get_run(self._run_id_a)
            trace_b = db.get_run(self._run_id_b)

            if trace_a and trace_b:
                self.query_one("#info-a", Static).update(
                    f"  {trace_a.surface_type.value}: {trace_a.target[:30]}"
                )
                self.query_one("#info-b", Static).update(
                    f"  {trace_b.surface_type.value}: {trace_b.target[:30]}"
                )

                comparison = compare_traces(trace_a, trace_b)

                table = self.query_one("#deltas-table", DataTable)
                table.clear(columns=True)
                table.add_columns("Metric", "A", "B", "Delta")

                scores_a = trace_a.scores.as_dict()
                scores_b = trace_b.scores.as_dict()
                for key in scores_a:
                    if key in scores_b:
                        va = scores_a[key].value
                        vb = scores_b[key].value
                        delta = vb - va
                        sign = "+" if delta >= 0 else ""
                        table.add_row(
                            scores_a[key].name[:15],
                            f"{va:.0f}",
                            f"{vb:.0f}",
                            f"{sign}{delta:.0f}",
                        )

                insights = self.query_one("#comparison-insights", Static)
                text = "\n".join(f"  - {i}" for i in comparison.insights[:10])
                if comparison.winner:
                    text += f"\n\n  Winner: {'A' if comparison.winner == 'a' else 'B'}"
                insights.update(text or "[dim]No insights[/]")

        except Exception:
            pass

    def action_go_back(self) -> None:
        self.app.pop_screen()
