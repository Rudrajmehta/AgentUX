"""Main Textual TUI application for AgentUX."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, TabbedContent, TabPane

from agentux.tui.screens.alerts import AlertsScreen
from agentux.tui.screens.home import HomeScreen
from agentux.tui.screens.trends import TrendsScreen


class AgentUXApp(App):
    """AgentUX Terminal UI — synthetic observability for agent usability."""

    TITLE = "AgentUX"
    SUB_TITLE = "Synthetic observability for agent usability"

    CSS_PATH = Path(__file__).parent / "styles" / "theme.tcss"

    BINDINGS = [
        Binding("1", "show_tab('home')", "Home", show=True),
        Binding("2", "show_tab('trends')", "Trends", show=True),
        Binding("3", "show_tab('alerts')", "Alerts", show=True),
        Binding("d", "toggle_dark", "Dark/Light"),
        Binding("q", "quit", "Quit"),
    ]

    SCREENS = {
        "home": HomeScreen,
        "trends": TrendsScreen,
        "alerts": AlertsScreen,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="home"):
            with TabPane("Home", id="home"):
                yield HomeScreen()
            with TabPane("Trends", id="trends"):
                yield TrendsScreen()
            with TabPane("Alerts", id="alerts"):
                yield AlertsScreen()
        yield Footer()

    def action_show_tab(self, tab: str) -> None:
        self.query_one(TabbedContent).active = tab

    def action_toggle_dark(self) -> None:
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"
