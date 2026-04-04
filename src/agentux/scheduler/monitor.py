"""Monitor configuration loading and management."""

from __future__ import annotations

from pathlib import Path

import yaml

from agentux.core.models import MonitorConfig, SurfaceType


def load_monitors_from_dir(directory: Path) -> list[MonitorConfig]:
    """Load all monitor configs from a directory."""
    monitors = []
    if not directory.exists():
        return monitors

    for path in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        try:
            raw = yaml.safe_load(path.read_text())
            if isinstance(raw, dict) and "name" in raw:
                monitors.append(MonitorConfig(
                    name=raw["name"],
                    surface=SurfaceType(raw["surface"]),
                    target=raw["target"],
                    task=raw["task"],
                    schedule=raw.get("schedule", "0 */6 * * *"),
                    backend=raw.get("backend", "openai"),
                    model=raw.get("model", "gpt-4.1"),
                    enabled=raw.get("enabled", True),
                    thresholds=raw.get("thresholds", {}),
                    tags=raw.get("tags", []),
                ))
        except Exception:
            pass

    return monitors
