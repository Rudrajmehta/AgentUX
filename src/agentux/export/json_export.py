"""JSON export for run traces."""

from __future__ import annotations

import json
from typing import Any

from agentux.core.models import RunTrace


def export_json(trace: RunTrace, analysis: dict[str, Any] | None = None) -> str:
    """Export a run trace as formatted JSON."""
    data = json.loads(trace.model_dump_json())
    if analysis:
        data["analysis"] = analysis
    return json.dumps(data, indent=2, default=str)
