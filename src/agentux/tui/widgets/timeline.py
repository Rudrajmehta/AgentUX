"""Timeline widget for step-by-step visualization."""

from __future__ import annotations

from textual.widgets import Static

from agentux.core.models import StepRecord


class TimelineWidget(Static):
    """Renders a vertical timeline of run steps."""

    DEFAULT_CSS = """
    TimelineWidget {
        height: auto;
        padding: 1;
    }
    """

    def __init__(self, steps: list[StepRecord] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._steps = steps or []

    def render(self) -> str:
        if not self._steps:
            return "[dim]No steps recorded[/]"

        lines = []
        for step in self._steps:
            icon = "[#00ff88]O[/]" if step.success else "[#ff4444]X[/]"
            connector = "|" if step.step_number < len(self._steps) else " "
            line = (
                f"  {icon} Step {step.step_number}: "
                f"[bold]{step.action_type}[/] {step.action[:30]}"
            )
            lines.append(line)
            if step.thought_summary:
                lines.append(f"  {connector}   [dim]{step.thought_summary[:50]}[/]")
            if step.extracted_facts:
                for fact in step.extracted_facts[:1]:
                    lines.append(f"  {connector}   [cyan]+ {fact[:45]}[/]")
            if step.errors:
                for err in step.errors[:1]:
                    lines.append(f"  {connector}   [red]! {err[:45]}[/]")
            lines.append(f"  {connector}")

        return "\n".join(lines)

    def update_steps(self, steps: list[StepRecord]) -> None:
        self._steps = steps
        self.refresh()
