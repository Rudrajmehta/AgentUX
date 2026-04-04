"""Status pill widget for compact status display."""

from __future__ import annotations

from textual.widgets import Static

STATUS_STYLES = {
    "ok": ("#00ff88", "OK"),
    "pass": ("#00ff88", "PASS"),
    "fail": ("#ff4444", "FAIL"),
    "running": ("#00aaff", "RUN"),
    "pending": ("#888888", "WAIT"),
    "warning": ("#ffaa00", "WARN"),
    "critical": ("#ff4444", "CRIT"),
    "info": ("#0d7377", "INFO"),
}


class StatusPill(Static):
    """A compact colored status indicator."""

    DEFAULT_CSS = """
    StatusPill {
        width: auto;
        height: 1;
        padding: 0 1;
    }
    """

    def __init__(self, status: str = "ok", **kwargs) -> None:
        super().__init__(**kwargs)
        self._status = status.lower()

    def render(self) -> str:
        color, label = STATUS_STYLES.get(self._status, ("#888888", self._status.upper()))
        return f"[{color} bold] {label} [/]"

    def update_status(self, status: str) -> None:
        self._status = status.lower()
        self.refresh()
