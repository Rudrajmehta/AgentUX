"""Mock surface adapter for demo/test mode — no real I/O."""

from __future__ import annotations

from typing import Any

from agentux.core.models import Affordance, AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface

# Canned affordances per surface type
_MOCK_AFFORDANCES: dict[str, list[dict[str, Any]]] = {
    "browser": [
        {"name": "header", "kind": "section", "relevant": True},
        {"name": "navigation", "kind": "section", "relevant": True},
        {"name": "hero", "kind": "section", "relevant": True},
        {"name": "pricing", "kind": "section", "relevant": True},
        {"name": "features", "kind": "section", "relevant": True},
        {"name": "cta", "kind": "section", "relevant": True},
        {"name": "footer", "kind": "section", "relevant": False},
        {"name": "Pricing", "kind": "link", "relevant": True},
        {"name": "Contact", "kind": "link", "relevant": True},
    ],
    "markdown": [
        {"name": "Introduction", "kind": "section", "relevant": True},
        {"name": "Installation", "kind": "section", "relevant": True},
        {"name": "Quick Start", "kind": "section", "relevant": True},
        {"name": "Configuration", "kind": "section", "relevant": True},
        {"name": "API Reference", "kind": "section", "relevant": True},
        {"name": "FAQ", "kind": "section", "relevant": True},
    ],
    "cli": [
        {"name": "init", "kind": "command", "relevant": True},
        {"name": "add", "kind": "command", "relevant": True},
        {"name": "remove", "kind": "command", "relevant": False},
        {"name": "run", "kind": "command", "relevant": False},
        {"name": "--help", "kind": "flag", "relevant": True},
        {"name": "--version", "kind": "flag", "relevant": False},
    ],
    "mcp": [
        {"name": "search", "kind": "tool", "relevant": True},
        {"name": "create", "kind": "tool", "relevant": False},
        {"name": "delete", "kind": "tool", "relevant": False},
        {"name": "list", "kind": "tool", "relevant": False},
    ],
}

_MOCK_OBSERVATIONS: dict[str, str] = {
    "browser": (
        "URL: https://example.com\n"
        "Title: Example Corp - Build Faster\n"
        "Description: The modern platform for developers\n\n"
        "Visible text:\n"
        "Example Corp\nHome Features Pricing Docs Contact\n"
        "Build Faster, Ship Smarter\n"
        "The modern platform for developers.\n"
        "Pricing: Free, Pro ($29/mo), Enterprise (custom)\n"
        "Contact sales@example.com for enterprise inquiries.\n"
        "© 2024 Example Corp"
    ),
    "markdown": (
        "Markdown document: README.md\n"
        "Total length: 4200 chars\n"
        "Sections: 6\n\n"
        "Table of contents:\n"
        "  - Introduction\n"
        "  - Installation\n"
        "  - Quick Start\n"
        "  - Configuration\n"
        "  - API Reference\n"
        "  - FAQ"
    ),
    "cli": (
        "CLI Tool: mytool\n"
        "Commands discovered: 4\n"
        "Flags discovered: 2\n"
        "Commands executed: 0"
    ),
    "mcp": (
        "MCP Server: server.py\n"
        "Tools available: 4\n"
        "Tool calls made: 0\n\n"
        "Available tools:\n"
        "  - search: Search documents by query\n"
        "  - create: Create a new record\n"
        "  - delete: Delete a record\n"
        "  - list: List all records"
    ),
}


class MockSurface(Surface):
    """Mock surface for demo/test mode. No real browser, CLI, or MCP connection."""

    def __init__(self, surface_type: SurfaceType, target: str) -> None:
        self.surface_type = surface_type
        self.target = target
        self._affordances: list[Affordance] = []
        self._action_count = 0

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def discover(self) -> list[Affordance]:
        key = self.surface_type.value
        for item in _MOCK_AFFORDANCES.get(key, []):
            self._affordances.append(Affordance(
                name=item["name"],
                kind=item["kind"],
                status=AffordanceStatus.DISCOVERED,
                relevant=item["relevant"],
            ))
        return self._affordances

    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        self._action_count += 1
        # Mark some affordances as interacted
        if self._affordances and self._action_count <= len(self._affordances):
            self._affordances[self._action_count - 1].status = AffordanceStatus.INTERACTED

        if action == "done":
            return "Task completed"
        return f"Mock result for {action} (demo mode)"

    async def observe(self) -> str:
        return _MOCK_OBSERVATIONS.get(self.surface_type.value, "Mock observation")

    async def summarize_state(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type.value,
            "target": self.target,
            "demo_mode": True,
            "affordances_found": len(self._affordances),
            "actions_taken": self._action_count,
        }

    async def list_affordances(self) -> list[Affordance]:
        return self._affordances
