"""Main Textual TUI application for AgentUX."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from agentux.tui.screens.alerts import AlertsPanel
from agentux.tui.screens.home import HomePanel
from agentux.tui.screens.trends import TrendsPanel


class AgentUXApp(App):
    """AgentUX Terminal UI — synthetic observability for agent usability."""

    TITLE = "AgentUX"
    SUB_TITLE = "Synthetic observability for agent usability"

    CSS_PATH = Path(__file__).parent / "styles" / "theme.tcss"

    BINDINGS = [
        Binding("1", "show_tab('home')", "Home", show=True),
        Binding("2", "show_tab('trends')", "Trends", show=True),
        Binding("3", "show_tab('alerts')", "Alerts", show=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("d", "toggle_dark", "Dark/Light"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="home"):
            with TabPane("Home", id="home"):
                yield HomePanel()
            with TabPane("Trends", id="trends"):
                yield TrendsPanel()
            with TabPane("Alerts", id="alerts"):
                yield AlertsPanel()
        yield Footer()

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_refresh(self) -> None:
        for panel in self.query("HomePanel, TrendsPanel, AlertsPanel"):
            if hasattr(panel, "load_data"):
                panel.load_data()

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"
