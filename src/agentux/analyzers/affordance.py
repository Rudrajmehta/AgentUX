"""Affordance analysis: discovered vs missed elements."""

from __future__ import annotations

from typing import Any

from agentux.analyzers.base import Analyzer
from agentux.core.models import AffordanceStatus, RunTrace


class AffordanceAnalyzer(Analyzer):
    """Analyzes which affordances were discovered, used, or missed."""

    name = "affordance"

    def analyze(self, trace: RunTrace) -> dict[str, Any]:
        discovered = []
        interacted = []
        missed = []
        ignored = []
        ambiguous = []

        for aff in trace.affordances:
            entry = {"name": aff.name, "kind": aff.kind, "relevant": aff.relevant}
            if aff.status == AffordanceStatus.DISCOVERED:
                discovered.append(entry)
            elif aff.status == AffordanceStatus.INTERACTED:
                interacted.append(entry)
            elif aff.status == AffordanceStatus.MISSED:
                missed.append(entry)
            elif aff.status == AffordanceStatus.IGNORED:
                ignored.append(entry)
            elif aff.status == AffordanceStatus.AMBIGUOUS:
                ambiguous.append(entry)

        relevant_total = sum(1 for a in trace.affordances if a.relevant)
        relevant_found = sum(
            1
            for a in trace.affordances
            if a.relevant and a.status in (AffordanceStatus.DISCOVERED, AffordanceStatus.INTERACTED)
        )

        insights = []
        if missed:
            missed_names: list[str] = [str(m["name"]) for m in missed if m["relevant"]]
            if missed_names:
                insights.append(f"Missed relevant affordances: {', '.join(missed_names[:5])}")
        if ambiguous:
            insights.append(f"{len(ambiguous)} affordances were ambiguous to the agent")
        if relevant_total > 0:
            coverage_pct = relevant_found / relevant_total * 100
            insights.append(f"Relevant affordance coverage: {coverage_pct:.0f}%")

        return {
            "discovered": discovered,
            "interacted": interacted,
            "missed": missed,
            "ignored": ignored,
            "ambiguous": ambiguous,
            "relevant_total": relevant_total,
            "relevant_found": relevant_found,
            "coverage_pct": (relevant_found / relevant_total * 100) if relevant_total else 0,
            "insights": insights,
        }
