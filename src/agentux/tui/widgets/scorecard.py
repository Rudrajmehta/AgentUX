"""Scorecard widget for displaying metrics."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import Static

from agentux.core.models import ScoreCard


def _score_color(value: float) -> str:
    if value >= 70:
        return "#00ff88"
    if value >= 40:
        return "#ffaa00"
    return "#ff4444"


class ScoreBox(Static):
    """A single score display box."""

    DEFAULT_CSS = """
    ScoreBox {
        width: 1fr;
        height: 5;
        border: solid #333355;
        content-align: center middle;
        margin: 0 1;
        padding: 0 1;
    }
    """

    def __init__(self, name: str, value: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self._score_name = name
        self._score_value = value

    def render(self) -> str:
        color = _score_color(self._score_value)
        return f"[bold]{self._score_name}[/]\n[{color}]{self._score_value:.0f}[/]"


class ScoreCardWidget(Static):
    """Displays a full scorecard as a row of score boxes."""

    DEFAULT_CSS = """
    ScoreCardWidget {
        height: auto;
        margin: 1 0;
        layout: horizontal;
    }
    """

    def __init__(self, scores: ScoreCard | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._scores = scores

    def compose(self) -> ComposeResult:
        if not self._scores:
            yield Static("[dim]No scores available[/]")
            return

        for _key, result in self._scores.as_dict().items():
            yield ScoreBox(result.name[:12], result.value)

    def update_scores(self, scores: ScoreCard) -> None:
        self._scores = scores
        self.refresh(layout=True)
