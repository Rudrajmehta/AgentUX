"""Surface adapters for different target types."""

from agentux.surfaces.base import Surface
from agentux.surfaces.browser import BrowserSurface
from agentux.surfaces.cli_surface import CLISurface
from agentux.surfaces.markdown import MarkdownSurface
from agentux.surfaces.mcp import MCPSurface

__all__ = ["Surface", "BrowserSurface", "MarkdownSurface", "CLISurface", "MCPSurface"]
