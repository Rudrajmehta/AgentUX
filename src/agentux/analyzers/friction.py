"""Friction analysis: retries, dead ends, confusion points."""

from __future__ import annotations

from typing import Any

from agentux.analyzers.base import Analyzer
from agentux.core.models import RunTrace


class FrictionAnalyzer(Analyzer):
    """Analyzes friction points in the agent's interaction."""

    name = "friction"

    def analyze(self, trace: RunTrace) -> dict[str, Any]:
        retries = 0
        backtracks = 0
        dead_ends = 0
        confusion_points: list[dict[str, Any]] = []
        error_messages: list[str] = []

        prev_action = ""
        for i, step in enumerate(trace.steps):
            # Detect retries (same action repeated)
            current_action = f"{step.action_type}:{step.action}"
            if current_action == prev_action and not step.success:
                retries += 1

            # Detect backtracks
            if step.action_type == "back" or step.action == "back":
                backtracks += 1

            # Detect dead ends (failure followed by different approach)
            if not step.success and i + 1 < len(trace.steps):
                next_step = trace.steps[i + 1]
                if next_step.action_type != step.action_type:
                    dead_ends += 1

            # Detect confusion (high uncertainty or warnings)
            if step.warnings or step.metadata.get("uncertainty", 0) > 0.7:
                confusion_points.append({
                    "step": step.step_number,
                    "action": step.action,
                    "warnings": step.warnings,
                    "uncertainty": step.metadata.get("uncertainty", 0),
                })

            # Collect errors
            for err in step.errors:
                error_messages.append(f"Step {step.step_number}: {err}")

            prev_action = current_action

        total_steps = len(trace.steps) or 1
        friction_score = (
            (retries * 2 + backtracks * 3 + dead_ends * 4 + len(confusion_points) * 1)
            / total_steps
            * 100
        )

        insights = []
        if retries > 0:
            insights.append(f"Agent retried {retries} actions (possible UI confusion)")
        if backtracks > 0:
            insights.append(f"Agent backtracked {backtracks} times (navigation issues)")
        if dead_ends > 0:
            insights.append(f"Hit {dead_ends} dead ends requiring strategy change")
        if confusion_points:
            insights.append(
                f"{len(confusion_points)} high-confusion steps detected"
            )
        if not insights:
            insights.append("Smooth interaction with minimal friction")

        return {
            "retries": retries,
            "backtracks": backtracks,
            "dead_ends": dead_ends,
            "confusion_points": confusion_points,
            "error_messages": error_messages[:20],
            "friction_index": min(100, friction_score),
            "insights": insights,
        }
