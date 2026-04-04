"""Base analyzer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentux.core.models import RunTrace


class Analyzer(ABC):
    """Base class for trace analyzers."""

    name: str = "base"

    @abstractmethod
    def analyze(self, trace: RunTrace) -> dict[str, Any]:
        """Analyze a run trace and return findings."""
