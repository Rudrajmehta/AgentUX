"""Live run view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, ProgressBar, RichLog, Static

from agentux.tui.widgets.scorecard import ScoreCardWidget


class LiveRunScreen(Screen):
    """Shows live progress of a running benchmark."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
        ("q", "go_back", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static("[bold cyan] Live Run[/]\n", id="title")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("[bold]Run Info[/]")
                    yield Static("Target: -", id="run-target")
                    yield Static("Task: -", id="run-task")
                    yield Static("Surface: -", id="run-surface")
                    yield Static("Model: -", id="run-model")

                with Vertical(classes="panel"):
                    yield Static("[bold]Progress[/]")
                    yield Static("Step: 0 / 25", id="step-counter")
                    yield ProgressBar(total=25, id="step-progress")
                    yield Static("Tokens: 0", id="token-counter")
                    yield Static("Time: 0s", id="time-counter")

            yield ScoreCardWidget(id="live-scores")

            yield Static("[bold]Step Log[/]")
            yield RichLog(id="run-log", highlight=True, markup=True)

        yield Footer()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def update_step(
        self, step_num: int, max_steps: int, action: str, success: bool, tokens: int, elapsed: float
    ) -> None:
        """Update the live display with step info."""
        self.query_one("#step-counter", Static).update(f"Step: {step_num} / {max_steps}")
        self.query_one("#step-progress", ProgressBar).update(progress=step_num)
        self.query_one("#token-counter", Static).update(f"Tokens: {tokens}")
        self.query_one("#time-counter", Static).update(f"Time: {elapsed:.1f}s")

        log = self.query_one("#run-log", RichLog)
        icon = "[green]OK[/]" if success else "[red]FAIL[/]"
        log.write(f"  {step_num}. {icon} {action}")
