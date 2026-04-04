"""Coverage analysis: surface-specific coverage metrics."""

from __future__ import annotations

from typing import Any

from agentux.analyzers.base import Analyzer
from agentux.core.models import AffordanceStatus, RunTrace, SurfaceType


class CoverageAnalyzer(Analyzer):
    """Analyzes surface coverage — what was seen, used, and missed."""

    name = "coverage"

    def analyze(self, trace: RunTrace) -> dict[str, Any]:
        if trace.surface_type == SurfaceType.BROWSER:
            return self._analyze_browser(trace)
        elif trace.surface_type == SurfaceType.MARKDOWN:
            return self._analyze_markdown(trace)
        elif trace.surface_type == SurfaceType.CLI:
            return self._analyze_cli(trace)
        elif trace.surface_type == SurfaceType.MCP:
            return self._analyze_mcp(trace)
        return {"coverage_type": "unknown"}

    def _analyze_browser(self, trace: RunTrace) -> dict[str, Any]:
        sections = [a for a in trace.affordances if a.kind == "section"]
        links = [a for a in trace.affordances if a.kind == "link"]

        viewed = [s for s in sections if s.status != AffordanceStatus.MISSED]
        interacted = [s for s in sections if s.status == AffordanceStatus.INTERACTED]
        missed = [s for s in sections if s.status == AffordanceStatus.MISSED and s.relevant]

        return {
            "coverage_type": "browser",
            "sections_total": len(sections),
            "sections_viewed": len(viewed),
            "sections_interacted": len(interacted),
            "sections_missed": len(missed),
            "links_found": len(links),
            "pages_visited": len(
                set(s.metadata.get("url", "") for s in trace.steps if s.metadata.get("url"))
            ),
            "heatmap": [
                {
                    "name": s.name,
                    "status": s.status.value,
                    "relevant": s.relevant,
                }
                for s in sections
            ],
            "missed_relevant": [s.name for s in missed],
        }

    def _analyze_markdown(self, trace: RunTrace) -> dict[str, Any]:
        sections = [a for a in trace.affordances if a.kind == "section"]
        code_blocks = [a for a in trace.affordances if a.kind == "code_block"]

        read = [s for s in sections if s.status == AffordanceStatus.INTERACTED]
        total = len(sections) or 1

        return {
            "coverage_type": "markdown",
            "sections_total": len(sections),
            "sections_read": len(read),
            "coverage_pct": len(read) / total * 100,
            "code_blocks_found": len(code_blocks),
            "section_map": [
                {"name": s.name, "status": s.status.value, "level": s.metadata.get("level", 0)}
                for s in sections
            ],
        }

    def _analyze_cli(self, trace: RunTrace) -> dict[str, Any]:
        commands = [a for a in trace.affordances if a.kind == "command"]
        flags = [a for a in trace.affordances if a.kind == "flag"]
        executed = [s for s in trace.steps if s.action_type == "execute"]

        return {
            "coverage_type": "cli",
            "commands_discovered": len(commands),
            "flags_discovered": len(flags),
            "commands_executed": len(executed),
            "commands_succeeded": sum(1 for s in executed if s.success),
            "commands_failed": sum(1 for s in executed if not s.success),
            "affordance_map": [
                {
                    "name": a.name,
                    "kind": a.kind,
                    "status": a.status.value,
                    "relevant": a.relevant,
                }
                for a in commands + flags
            ],
        }

    def _analyze_mcp(self, trace: RunTrace) -> dict[str, Any]:
        tools = [a for a in trace.affordances if a.kind == "tool"]
        calls = [s for s in trace.steps if s.action_type == "tool_call"]

        used = [t for t in tools if t.status == AffordanceStatus.INTERACTED]
        unused = [t for t in tools if t.status != AffordanceStatus.INTERACTED]

        return {
            "coverage_type": "mcp",
            "tools_available": len(tools),
            "tools_used": len(used),
            "tools_unused": len(unused),
            "total_calls": len(calls),
            "successful_calls": sum(1 for c in calls if c.success),
            "failed_calls": sum(1 for c in calls if not c.success),
            "tool_map": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "description": t.notes[:60],
                }
                for t in tools
            ],
            "unused_relevant": [t.name for t in unused if t.relevant],
        }
