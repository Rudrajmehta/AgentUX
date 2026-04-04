"""Metric computation functions for scoring."""

from __future__ import annotations

from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
    ScoreResult,
    StepRecord,
)


def compute_discoverability(trace: RunTrace) -> ScoreResult:
    """Compute discoverability score from trace data."""
    relevant = [a for a in trace.affordances if a.relevant]
    total_relevant = len(relevant) or 1
    discovered = [
        a for a in relevant
        if a.status in (AffordanceStatus.DISCOVERED, AffordanceStatus.INTERACTED)
    ]

    coverage = len(discovered) / total_relevant

    # Speed factor: bonus for early discovery
    first_discovery_step = None
    for step in trace.steps:
        if step.affordances_discovered:
            first_discovery_step = step.step_number
            break
    total_steps = len(trace.steps) or 1
    speed_factor = max(0, 1 - (first_discovery_step or total_steps) / total_steps)

    score = coverage * 80 + speed_factor * 20

    return ScoreResult(
        name="Discoverability",
        value=min(100, max(0, score)),
        weight=0.20,
        explanation=(
            f"Discovered {len(discovered)}/{total_relevant} relevant affordances. "
            f"First discovery at step {first_discovery_step or 'N/A'}."
        ),
        inputs={
            "discovered_relevant": len(discovered),
            "total_relevant": total_relevant,
            "first_discovery_step": first_discovery_step,
            "total_steps": total_steps,
        },
    )


def compute_actionability(trace: RunTrace) -> ScoreResult:
    """Compute actionability score from trace data."""
    action_steps = [s for s in trace.steps if s.action_type not in ("read", "done", "")]
    total_actions = len(action_steps) or 1
    successful = sum(1 for s in action_steps if s.success)
    first_try = sum(1 for s in action_steps if s.success and not s.errors)

    score = (successful / total_actions) * 70 + (first_try / total_actions) * 30

    return ScoreResult(
        name="Actionability",
        value=min(100, max(0, score)),
        weight=0.20,
        explanation=(
            f"{successful}/{total_actions} actions succeeded. "
            f"{first_try} correct on first try."
        ),
        inputs={
            "successful_actions": successful,
            "total_actions": total_actions,
            "correct_on_first_try": first_try,
        },
    )


def compute_recovery(trace: RunTrace) -> ScoreResult:
    """Compute recovery score from trace data."""
    dead_ends = 0
    unrecoverable = 0
    helpful_errors = 0

    for i, step in enumerate(trace.steps):
        if step.errors:
            # Check if next step recovered
            if i + 1 < len(trace.steps) and trace.steps[i + 1].success:
                helpful_errors += 1
            elif i + 1 >= len(trace.steps) or not trace.steps[i + 1].success:
                dead_ends += 1
        if step.action_type == "back":
            dead_ends += 1

    # Check for unrecoverable (consecutive failures)
    consecutive_fails = 0
    for step in trace.steps:
        if not step.success:
            consecutive_fails += 1
            if consecutive_fails >= 3:
                unrecoverable += 1
                consecutive_fails = 0
        else:
            consecutive_fails = 0

    score = max(0, 100 - (dead_ends * 15) - (unrecoverable * 25) + (helpful_errors * 10))

    return ScoreResult(
        name="Recovery",
        value=min(100, max(0, score)),
        weight=0.15,
        explanation=(
            f"{dead_ends} dead ends, {unrecoverable} unrecoverable errors, "
            f"{helpful_errors} helpful error messages."
        ),
        inputs={
            "dead_ends": dead_ends,
            "unrecoverable_errors": unrecoverable,
            "helpful_error_messages": helpful_errors,
        },
    )


def compute_efficiency(trace: RunTrace) -> ScoreResult:
    """Compute efficiency score from trace data."""
    total_steps = len(trace.steps)
    # Estimate optimal steps: task-dependent, but rough heuristic
    optimal = max(2, total_steps // 3)  # Generous estimate
    excess = max(0, total_steps - optimal)

    backtracks = sum(1 for s in trace.steps if s.action_type == "back")
    redundant_reads = 0
    seen_observations: set[str] = set()
    for step in trace.steps:
        key = f"{step.action}:{step.action_type}"
        if key in seen_observations and step.action_type == "read":
            redundant_reads += 1
        seen_observations.add(key)

    score = max(0, 100 - (excess * 8) - (backtracks * 12) - (redundant_reads * 5))

    return ScoreResult(
        name="Efficiency",
        value=min(100, max(0, score)),
        weight=0.15,
        explanation=(
            f"{total_steps} steps taken (est. optimal: {optimal}). "
            f"{backtracks} backtracks, {redundant_reads} redundant reads."
        ),
        inputs={
            "actual_steps": total_steps,
            "optimal_steps": optimal,
            "backtracks": backtracks,
            "redundant_reads": redundant_reads,
            "excess_steps": excess,
        },
    )


def compute_documentation_clarity(trace: RunTrace) -> ScoreResult:
    """Compute documentation clarity score."""
    all_facts = []
    for step in trace.steps:
        all_facts.extend(step.extracted_facts)
    facts_count = len(all_facts)
    expected_facts = max(3, len(trace.steps) // 2)  # Heuristic

    total_steps = len(trace.steps) or 1
    low_uncertainty = sum(
        1 for s in trace.steps
        if s.metadata.get("uncertainty", 0.5) < 0.3
    )
    # Default: assume moderate clarity if no uncertainty data
    if low_uncertainty == 0 and total_steps > 0:
        low_uncertainty = total_steps // 2

    fact_coverage = min(1.0, facts_count / expected_facts)
    clarity_ratio = low_uncertainty / total_steps

    score = fact_coverage * 60 + clarity_ratio * 40

    return ScoreResult(
        name="Documentation Clarity",
        value=min(100, max(0, score)),
        weight=0.15,
        explanation=(
            f"Extracted {facts_count} facts (expected ~{expected_facts}). "
            f"{low_uncertainty}/{total_steps} low-uncertainty steps."
        ),
        inputs={
            "facts_extracted": facts_count,
            "expected_facts": expected_facts,
            "low_uncertainty_steps": low_uncertainty,
            "total_steps": total_steps,
        },
    )


def compute_tool_clarity(trace: RunTrace) -> ScoreResult:
    """Compute tool clarity score (CLI and MCP only)."""
    tool_calls = [s for s in trace.steps if s.action_type in ("execute", "tool_call")]
    total = len(tool_calls) or 1
    correct = sum(1 for s in tool_calls if s.success)

    # Argument correctness: successful without errors
    arg_correct = sum(1 for s in tool_calls if s.success and not s.errors)
    arg_rate = arg_correct / total

    # Help usefulness: if help was consulted and next action succeeded
    help_useful = 0
    for i, step in enumerate(trace.steps):
        if step.action_type == "read" and "help" in step.action.lower():
            if i + 1 < len(trace.steps) and trace.steps[i + 1].success:
                help_useful += 1

    help_factor = min(1.0, help_useful / max(1, len(tool_calls) // 2))

    score = (correct / total) * 50 + arg_rate * 30 + help_factor * 20

    return ScoreResult(
        name="Tool Clarity",
        value=min(100, max(0, score)),
        weight=0.15,
        explanation=(
            f"{correct}/{total} correct selections, "
            f"{arg_rate:.0%} arg correctness, "
            f"{help_useful} helpful help consultations."
        ),
        inputs={
            "correct_tool_selections": correct,
            "total_selections": total,
            "arg_correctness_rate": arg_rate,
            "help_text_usefulness": help_useful,
        },
    )
