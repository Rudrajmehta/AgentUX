"""Scoring engine that computes all metrics for a run."""

from __future__ import annotations

from agentux.core.models import RunTrace, ScoreCard, ScoreResult, SurfaceType
from agentux.scoring.metrics import (
    compute_actionability,
    compute_discoverability,
    compute_documentation_clarity,
    compute_efficiency,
    compute_recovery,
    compute_tool_clarity,
)


class ScoringEngine:
    """Computes transparent, decomposable scores for a run trace."""

    def score(self, trace: RunTrace) -> ScoreCard:
        """Compute all applicable scores for a trace."""
        card = ScoreCard()
        card.discoverability = compute_discoverability(trace)
        card.actionability = compute_actionability(trace)
        card.recovery = compute_recovery(trace)
        card.efficiency = compute_efficiency(trace)
        card.documentation_clarity = compute_documentation_clarity(trace)

        if trace.surface_type in (SurfaceType.CLI, SurfaceType.MCP):
            card.tool_clarity = compute_tool_clarity(trace)

        card.aes = self._compute_aes(trace.surface_type, card)

        # Patch per-metric weights to match the actual AES weights for this surface type
        if trace.surface_type in (SurfaceType.CLI, SurfaceType.MCP):
            w = {"discoverability": 0.20, "actionability": 0.20, "recovery": 0.15,
                 "efficiency": 0.15, "documentation_clarity": 0.15, "tool_clarity": 0.15}
        else:
            w = {"discoverability": 0.25, "actionability": 0.25, "recovery": 0.15,
                 "efficiency": 0.15, "documentation_clarity": 0.20}
        for key, weight in w.items():
            score_result = getattr(card, key, None)
            if score_result is not None:
                score_result.weight = weight

        return card

    def _compute_aes(self, surface_type: SurfaceType, card: ScoreCard) -> ScoreResult:
        """Compute composite AES from component scores."""
        if surface_type in (SurfaceType.CLI, SurfaceType.MCP):
            # With tool clarity
            weights = {
                "discoverability": 0.20,
                "actionability": 0.20,
                "recovery": 0.15,
                "efficiency": 0.15,
                "documentation_clarity": 0.15,
                "tool_clarity": 0.15,
            }
        else:
            # Without tool clarity
            weights = {
                "discoverability": 0.25,
                "actionability": 0.25,
                "recovery": 0.15,
                "efficiency": 0.15,
                "documentation_clarity": 0.20,
            }

        weighted_sum = 0.0
        components: dict[str, float] = {}

        for key, weight in weights.items():
            score_result = getattr(card, key, None)
            if score_result is not None:
                value = score_result.value
                weighted_sum += value * weight
                components[key] = value

        explanation_parts = [
            f"{k}: {v:.0f} (x{weights[k]:.2f})" for k, v in components.items()
        ]

        return ScoreResult(
            name="Agent Efficacy Score (AES)",
            value=min(100, max(0, weighted_sum)),
            weight=1.0,
            explanation="Weighted composite: " + ", ".join(explanation_parts),
            inputs={"weights": weights, "components": components},
            sub_scores=components,
        )
