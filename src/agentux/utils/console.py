"""Shared Rich console and formatting helpers."""

from rich.console import Console
from rich.theme import Theme

AGENTUX_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "score.high": "bold green",
        "score.mid": "bold yellow",
        "score.low": "bold red",
        "surface.browser": "bold blue",
        "surface.markdown": "bold magenta",
        "surface.cli": "bold yellow",
        "surface.mcp": "bold cyan",
        "dim": "dim white",
        "accent": "bold cyan",
        "header": "bold white on dark_cyan",
    }
)

console = Console(theme=AGENTUX_THEME)


def score_style(value: float) -> str:
    """Return a style name based on score value (0-100)."""
    if value >= 70:
        return "score.high"
    if value >= 40:
        return "score.mid"
    return "score.low"


def surface_style(surface_type: str) -> str:
    """Return a style name for a surface type."""
    return f"surface.{surface_type}"


def format_duration(ms: float) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    return f"{minutes:.1f}m"


def format_tokens(tokens: int) -> str:
    """Format token count with K/M suffix."""
    if tokens < 1000:
        return str(tokens)
    if tokens < 1_000_000:
        return f"{tokens / 1000:.1f}K"
    return f"{tokens / 1_000_000:.1f}M"
