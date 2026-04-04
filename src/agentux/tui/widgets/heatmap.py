"""Heatmap widget for section/affordance coverage visualization."""

from __future__ import annotations

from textual.widgets import Static


HEAT_COLORS = {
    "interacted": "#00ff88",
    "discovered": "#0088ff",
    "missed": "#ff4444",
    "ignored": "#444466",
    "ambiguous": "#ffaa00",
}

HEAT_CHARS = {
    "interacted": "|||",
    "discovered": "...",
    "missed": "XXX",
    "ignored": "---",
    "ambiguous": "???",
}


class HeatmapWidget(Static):
    """Renders a section-level coverage heatmap."""

    DEFAULT_CSS = """
    HeatmapWidget {
        height: auto;
        padding: 1;
        border: solid #333355;
    }
    """

    def __init__(self, items: list[dict] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._items = items or []

    def render(self) -> str:
        if not self._items:
            return "[dim]No coverage data[/]"

        lines = ["[bold]Coverage Heatmap[/]\n"]
        for item in self._items[:20]:
            name = item.get("name", "?")[:20].ljust(20)
            status = item.get("status", "missed")
            color = HEAT_COLORS.get(status, "#888888")
            chars = HEAT_CHARS.get(status, "   ")
            lines.append(f"  [{color}]{chars}[/] {name} [{color}]{status}[/]")

        # Legend
        lines.append("")
        legend = " ".join(
            f"[{c}]{HEAT_CHARS[s]}={s}[/]" for s, c in HEAT_COLORS.items()
        )
        lines.append(f"  {legend}")

        return "\n".join(lines)

    def update_items(self, items: list[dict]) -> None:
        self._items = items
        self.refresh()
