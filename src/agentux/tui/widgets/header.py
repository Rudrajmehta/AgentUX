"""AgentUX TUI header widget."""

from textual.widgets import Static


class AgentUXHeader(Static):
    """Branded header bar for AgentUX TUI."""

    DEFAULT_CSS = """
    AgentUXHeader {
        dock: top;
        height: 3;
        background: #0d7377;
        color: #ffffff;
        content-align: center middle;
        text-style: bold;
        padding: 1;
    }
    """

    def render(self) -> str:
        return " AgentUX  Synthetic observability for agent usability"
