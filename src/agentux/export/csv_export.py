"""CSV export for run step data."""

from __future__ import annotations

import csv
import io

from agentux.core.models import RunTrace


def export_csv(trace: RunTrace) -> str:
    """Export run steps as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "step", "action_type", "action", "success", "thought_summary",
        "facts_count", "errors_count", "tokens", "latency_ms",
    ])

    for step in trace.steps:
        writer.writerow([
            step.step_number,
            step.action_type,
            step.action[:80],
            step.success,
            step.thought_summary[:80],
            len(step.extracted_facts),
            len(step.errors),
            step.tokens_used,
            f"{step.latency_ms:.0f}",
        ])

    return output.getvalue()
