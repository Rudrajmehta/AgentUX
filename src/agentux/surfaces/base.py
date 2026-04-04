"""Abstract base class for all surface adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentux.core.models import Affordance, SurfaceType


class Surface(ABC):
    """Base interface for surface adapters.

    Every surface type (browser, markdown, CLI, MCP) must implement
    this interface to provide a uniform interaction model.
    """

    surface_type: SurfaceType

    @abstractmethod
    async def setup(self) -> None:
        """Initialize the surface (launch browser, connect to MCP, etc.)."""

    @abstractmethod
    async def teardown(self) -> None:
        """Clean up resources."""

    @abstractmethod
    async def discover(self) -> list[Affordance]:
        """Discover available affordances on the surface.

        Returns a list of discovered elements: sections, commands,
        tools, links, forms, etc.
        """

    @abstractmethod
    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        """Perform an action on the surface.

        Args:
            action: The action to take (click, type, execute, call_tool, etc.)
            params: Action-specific parameters.

        Returns:
            A text description of the result.
        """

    @abstractmethod
    async def observe(self) -> str:
        """Observe the current state of the surface.

        Returns a text representation of what's currently visible/available.
        """

    @abstractmethod
    async def summarize_state(self) -> dict[str, Any]:
        """Get a structured summary of the current surface state."""

    @abstractmethod
    async def list_affordances(self) -> list[Affordance]:
        """List all known affordances with their current status."""

    async def __aenter__(self) -> Surface:
        await self.setup()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.teardown()
