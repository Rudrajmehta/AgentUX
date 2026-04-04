"""Replay view screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from agentux.tui.widgets.timeline import TimelineWidget


class ReplayScreen(Screen):
    """Step-by-step replay of a past run."""

    BINDINGS = [
        ("right", "next_step", "Next"),
        ("left", "prev_step", "Previous"),
        ("r", "reset", "Reset"),
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, run_id: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._run_id = run_id
        self._player = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Container():
            yield Static(f"[bold cyan] Replay — {self._run_id}[/]\n", id="title")

            with Horizontal():
                with Vertical(classes="panel"):
                    yield Static("[bold]Current Step[/]")
                    yield Static(id="step-detail")

                with Vertical(classes="panel"):
                    yield Static("[bold]State[/]")
                    yield Static(id="step-state")

            with Vertical(classes="panel"):
                yield Static("[bold]Timeline[/]")
                yield TimelineWidget(id="replay-timeline")

            yield Static(
                "[dim] Left/Right: navigate steps | R: reset | Esc: back[/]",
                id="replay-help",
            )

        yield Footer()

    def on_mount(self) -> None:
        self._load_run()

    def _load_run(self) -> None:
        if not self._run_id:
            return
        try:
            from agentux.core.config import load_config
            from agentux.replay.player import ReplayPlayer
            from agentux.storage.database import Database

            config = load_config()
            config.ensure_dirs()
            db = Database(config.database_url)
            trace = db.get_run(self._run_id)

            if trace:
                self._player = ReplayPlayer(trace)
                timeline = self.query_one("#replay-timeline", TimelineWidget)
                timeline.update_steps(trace.steps)
                self._show_step()
        except Exception:
            pass

    def _show_step(self) -> None:
        if not self._player:
            return

        pos = self._player.current_step
        if pos >= self._player.total_steps:
            pos = self._player.total_steps - 1
        if pos < 0:
            return

        step = self._player.trace.steps[pos]
        detail = self.query_one("#step-detail", Static)
        icon = "[green]OK[/]" if step.success else "[red]FAIL[/]"
        detail.update(
            f"  Step {step.step_number}/{self._player.total_steps} {icon}\n\n"
            f"  [bold]Thought:[/] {step.thought_summary}\n"
            f"  [bold]Action:[/] {step.action_type}: {step.action}\n"
            f"  [bold]Result:[/] {step.result[:120]}\n"
            f"  [bold]Facts:[/] {', '.join(step.extracted_facts[:3])}\n"
            f"  [bold]Tokens:[/] {step.tokens_used}  "
            f"[bold]Latency:[/] {step.latency_ms:.0f}ms"
        )

        state = self._player.get_state_at_step(pos + 1)
        state_widget = self.query_one("#step-state", Static)
        state_widget.update(
            f"  Facts: {len(state['facts_so_far'])}\n"
            f"  Affordances: {len(state['affordances_so_far'])}\n"
            f"  Tokens: {state['tokens_so_far']}\n"
            f"  Successes: {state['success_so_far']}\n"
            f"  Errors: {state['errors_so_far']}"
        )

    def action_next_step(self) -> None:
        if self._player and not self._player.is_at_end:
            self._player.next()
            self._show_step()

    def action_prev_step(self) -> None:
        if self._player and self._player.current_step > 0:
            self._player.previous()
            self._show_step()

    def action_reset(self) -> None:
        if self._player:
            self._player.reset()
            self._show_step()

    def action_go_back(self) -> None:
        self.app.pop_screen()
