"""Trace utilities for serialization and comparison."""

from __future__ import annotations

from typing import Any

from agentux.core.models import ComparisonResult, RunTrace


def compare_traces(trace_a: RunTrace, trace_b: RunTrace) -> ComparisonResult:
    """Compare two run traces and generate insights."""
    score_deltas: dict[str, float] = {}
    insights: list[str] = []

    scores_a = trace_a.scores.as_dict()
    scores_b = trace_b.scores.as_dict()

    for key in scores_a:
        if key in scores_b:
            delta = scores_b[key].value - scores_a[key].value
            score_deltas[key] = round(delta, 1)
            if abs(delta) > 5:
                direction = "improved" if delta > 0 else "declined"
                insights.append(
                    f"{key}: {direction} by {abs(delta):.0f} points "
                    f"({scores_a[key].value:.0f} -> {scores_b[key].value:.0f})"
                )

    # Compare efficiency
    if trace_a.step_count != trace_b.step_count:
        diff = trace_b.step_count - trace_a.step_count
        if diff < 0:
            insights.append(f"B used {abs(diff)} fewer steps ({trace_b.step_count} vs {trace_a.step_count})")
        else:
            insights.append(f"B used {diff} more steps ({trace_b.step_count} vs {trace_a.step_count})")

    # Compare tokens
    if trace_a.total_tokens and trace_b.total_tokens:
        token_diff_pct = (
            (trace_b.total_tokens - trace_a.total_tokens) / max(trace_a.total_tokens, 1) * 100
        )
        if abs(token_diff_pct) > 10:
            insights.append(f"Token usage {'increased' if token_diff_pct > 0 else 'decreased'} by {abs(token_diff_pct):.0f}%")

    # Compare success
    if trace_a.success != trace_b.success:
        if trace_b.success:
            insights.append("B succeeded where A failed")
        else:
            insights.append("B failed where A succeeded")

    # Determine winner
    aes_a = trace_a.scores.aes.value
    aes_b = trace_b.scores.aes.value
    winner = None
    if aes_b - aes_a > 3:
        winner = "b"
    elif aes_a - aes_b > 3:
        winner = "a"

    return ComparisonResult(
        run_a=trace_a,
        run_b=trace_b,
        task=trace_a.task,
        score_deltas=score_deltas,
        insights=insights,
        winner=winner,
    )
