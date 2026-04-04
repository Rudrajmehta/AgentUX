"""ASCII branding and terminal art for AgentUX."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

BANNER = r"""
     _                    _   _   ___  __
    / \   __ _  ___ _ __ | |_| | | \ \/ /
   / _ \ / _` |/ _ \ '_ \| __| | | |\  /
  / ___ \ (_| |  __/ | | | |_| |_| |/  \
 /_/   \_\__, |\___|_| |_|\__|\___//_/\_\
         |___/
"""

TAGLINE = "Synthetic observability for agent usability"
VERSION_LINE = "v0.1.0"


def print_banner(console: Console | None = None) -> None:
    """Print the AgentUX startup banner."""
    c = console or Console()
    banner_text = Text(BANNER, style="bold cyan")
    tagline_text = Text(f"  {TAGLINE}", style="dim white")
    version_text = Text(f"  {VERSION_LINE}\n", style="dim cyan")

    panel = Panel(
        Text.assemble(banner_text, "\n", tagline_text, "\n", version_text),
        border_style="cyan",
        padding=(0, 2),
    )
    c.print(panel)


def print_mini_banner(console: Console | None = None) -> None:
    """Print a compact one-line banner."""
    c = console or Console()
    c.print(
        Text.assemble(
            Text(" AgentUX ", style="bold white on dark_cyan"),
            Text(f" {VERSION_LINE} ", style="dim"),
            Text(f" {TAGLINE}", style="dim italic"),
        )
    )
