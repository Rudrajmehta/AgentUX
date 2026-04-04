"""Analyzer pipeline: runs all analyzers on a trace."""

from __future__ import annotations

from typing import Any

from agentux.analyzers.affordance import AffordanceAnalyzer
from agentux.analyzers.coverage import CoverageAnalyzer
from agentux.analyzers.friction import FrictionAnalyzer
from agentux.core.models import RunTrace


class AnalyzerPipeline:
    """Runs all registered analyzers on a trace and aggregates results."""

    def __init__(self) -> None:
        self.analyzers = [
            AffordanceAnalyzer(),
            FrictionAnalyzer(),
            CoverageAnalyzer(),
        ]

    def analyze(self, trace: RunTrace) -> dict[str, Any]:
        """Run all analyzers and return combined results."""
        results: dict[str, Any] = {}
        all_insights: list[str] = []

        for analyzer in self.analyzers:
            analysis = analyzer.analyze(trace)
            results[analyzer.name] = analysis
            all_insights.extend(analysis.get("insights", []))

        results["all_insights"] = all_insights
        return results
