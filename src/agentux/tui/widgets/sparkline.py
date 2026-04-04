"""Sparkline widget for inline trend visualization."""

from __future__ import annotations

from textual.widgets import Static


SPARK_CHARS = " _.-~*"


class SparklineWidget(Static):
    """Renders an ASCII sparkline from a list of values."""

    DEFAULT_CSS = """
    SparklineWidget {
        height: 1;
        padding: 0 1;
        color: #0d7377;
    }
    """

    def __init__(self, values: list[float] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._values = values or []

    def render(self) -> str:
        if not self._values:
            return "[dim]No data[/]"
        mn = min(self._values)
        mx = max(self._values)
        rng = mx - mn or 1
        chars = ""
        for v in self._values:
            idx = int((v - mn) / rng * (len(SPARK_CHARS) - 1))
            chars += SPARK_CHARS[idx]
        last = self._values[-1]
        return f"{chars}  {last:.0f}"

    def update_values(self, values: list[float]) -> None:
        self._values = values
        self.refresh()
