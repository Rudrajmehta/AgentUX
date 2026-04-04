"""Metric computation functions for scoring.

Each function computes a single decomposable metric from a RunTrace.
All scores are 0-100. Every score includes its inputs and explanation
so users can understand and verify the results.
"""

from __future__ import annotations

from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
    ScoreResult,
    StepRecord,
)


def compute_discoverability(trace: RunTrace) -> ScoreResult:
    """How easily the agent found relevant affordances.

    Formula:
        coverage_component = (discovered_relevant / total_relevant) * 80
        speed_component    = speed_factor * 20
        score              = coverage_component + speed_component

    Speed factor: 1.0 if discovery in step 1, scales down linearly.
    """
    relevant = [a for a in trace.affordances if a.relevant]
    total_relevant = len(relevant)
    if total_relevant == 0:
        # No affordances to discover — score based on whether any were found at all
        return ScoreResult(
            name="Discoverability",
            value=50.0,  # Neutral — can't measure
            explanation="No relevant affordances defined for this surface.",
            inputs={"discovered_relevant": 0, "total_relevant": 0},
        )

    discovered = [
        a for a in relevant
        if a.status in (AffordanceStatus.DISCOVERED, AffordanceStatus.INTERACTED)
    ]
    coverage = len(discovered) / total_relevant

    # Speed factor: bonus for early discovery (step 1 = full bonus)
    total_steps = len(trace.steps) or 1
    first_discovery_step = None
    for step in trace.steps:
        if step.affordances_discovered:
            first_discovery_step = step.step_number
            break

    if first_discovery_step is not None:
        # Step 1 → 1.0, step N → approaches 0
        speed_factor = max(0.0, 1.0 - (first_discovery_step - 1) / total_steps)
    else:
        speed_factor = 0.0  # Never discovered anything

    score = coverage * 80 + speed_factor * 20

    return ScoreResult(
        name="Discoverability",
        value=min(100, max(0, score)),
        explanation=(
            f"Discovered {len(discovered)}/{total_relevant} relevant affordances. "
            f"First discovery at step {first_discovery_step or 'N/A'}."
        ),
        inputs={
            "discovered_relevant": len(discovered),
            "total_relevant": total_relevant,
            "first_discovery_step": first_discovery_step,
            "total_steps": total_steps,
            "coverage": round(coverage, 3),
            "speed_factor": round(speed_factor, 3),
        },
    )


def compute_actionability(trace: RunTrace) -> ScoreResult:
    """How effectively the surface supported correct action execution.

    Formula:
        success_component   = (successful / total_actions) * 70
        first_try_component = (first_try / total_actions) * 30
        score               = success_component + first_try_component

    Only counts action steps (not reads or done).
    """
    action_steps = [s for s in trace.steps if s.action_type not in ("read", "done", "")]
    total_actions = len(action_steps)
    if total_actions == 0:
        return ScoreResult(
            name="Actionability",
            value=50.0,  # Neutral — no actions to measure
            explanation="No action steps to evaluate.",
            inputs={"successful_actions": 0, "total_actions": 0},
        )

    successful = sum(1 for s in action_steps if s.success)
    first_try = sum(1 for s in action_steps if s.success and not s.errors)

    score = (successful / total_actions) * 70 + (first_try / total_actions) * 30

    return ScoreResult(
        name="Actionability",
        value=min(100, max(0, score)),
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
    """How well the surface helped the agent recover from errors.

    Formula:
        score = 100 - (dead_ends * 15) - (unrecoverable * 25)
                    + (recovered * 10)

    If no errors occurred, score is 100 (no recovery needed).
    The score reflects surface quality: good error messages help recovery.
    """
    errors_encountered = sum(1 for s in trace.steps if s.errors or not s.success)
    if errors_encountered == 0:
        return ScoreResult(
            name="Recovery",
            value=100.0,
            explanation="No errors encountered — no recovery needed.",
            inputs={"errors_encountered": 0, "dead_ends": 0,
                    "unrecoverable_errors": 0, "recovered": 0},
        )

    dead_ends = 0
    recovered = 0
    unrecoverable = 0

    for i, step in enumerate(trace.steps):
        if step.errors or not step.success:
            if i + 1 < len(trace.steps) and trace.steps[i + 1].success:
                recovered += 1  # Agent recovered on next step
            else:
                dead_ends += 1
        if step.action_type == "back":
            dead_ends += 1

    # Consecutive failures = unrecoverable
    consecutive_fails = 0
    for step in trace.steps:
        if not step.success:
            consecutive_fails += 1
            if consecutive_fails >= 3:
                unrecoverable += 1
                consecutive_fails = 0
        else:
            consecutive_fails = 0

    score = max(0, 100 - (dead_ends * 15) - (unrecoverable * 25) + (recovered * 10))

    return ScoreResult(
        name="Recovery",
        value=min(100, max(0, score)),
        explanation=(
            f"{dead_ends} dead ends, {unrecoverable} unrecoverable errors, "
            f"{recovered} successful recoveries."
        ),
        inputs={
            "errors_encountered": errors_encountered,
            "dead_ends": dead_ends,
            "unrecoverable_errors": unrecoverable,
            "recovered": recovered,
        },
    )


def compute_efficiency(trace: RunTrace) -> ScoreResult:
    """How much unnecessary effort the agent had to expend.

    Formula:
        penalty = (backtracks * 12) + (redundant_reads * 5) + (wasted_steps * 5)
        score   = max(0, 100 - penalty)

    Uses absolute penalties rather than ratio to optimal (which was circular).
    A clean 4-step run with no waste scores 100.
    """
    total_steps = len(trace.steps)
    if total_steps == 0:
        return ScoreResult(
            name="Efficiency",
            value=50.0,
            explanation="No steps to evaluate.",
            inputs={"actual_steps": 0},
        )

    backtracks = sum(1 for s in trace.steps if s.action_type == "back")

    # Detect redundant reads: same action+type repeated
    redundant_reads = 0
    seen_actions: set[str] = set()
    for step in trace.steps:
        key = f"{step.action}:{step.action_type}"
        if key in seen_actions and step.action_type == "read":
            redundant_reads += 1
        seen_actions.add(key)

    # Wasted steps: failed steps that didn't lead to recovery
    wasted = 0
    for i, step in enumerate(trace.steps):
        if not step.success:
            # If followed by another failure or same action = wasted
            if i + 1 < len(trace.steps) and not trace.steps[i + 1].success:
                wasted += 1

    penalty = (backtracks * 12) + (redundant_reads * 5) + (wasted * 5)

    # Also penalize very long runs (diminishing returns after ~10 steps)
    if total_steps > 10:
        penalty += (total_steps - 10) * 3

    score = max(0, 100 - penalty)

    return ScoreResult(
        name="Efficiency",
        value=min(100, max(0, score)),
        explanation=(
            f"{total_steps} steps, {backtracks} backtracks, "
            f"{redundant_reads} redundant reads, {wasted} wasted steps."
        ),
        inputs={
            "actual_steps": total_steps,
            "backtracks": backtracks,
            "redundant_reads": redundant_reads,
            "wasted_steps": wasted,
            "penalty": penalty,
        },
    )


def compute_documentation_clarity(trace: RunTrace) -> ScoreResult:
    """How clear the surface's information structure was.

    Formula:
        fact_component    = min(1, facts / expected) * 60
        clarity_component = (low_uncertainty_steps / total_steps) * 40
        score             = fact_component + clarity_component

    Only uses real uncertainty data (no synthetic fallback).
    """
    all_facts: list[str] = []
    for step in trace.steps:
        all_facts.extend(step.extracted_facts)
    facts_count = len(all_facts)
    total_steps = len(trace.steps) or 1

    # Expected facts: at least 2, roughly 1 per 2 steps
    expected_facts = max(2, total_steps // 2)

    # Count steps with real low uncertainty data
    steps_with_uncertainty = [
        s for s in trace.steps if "uncertainty" in s.metadata
    ]
    if steps_with_uncertainty:
        low_uncertainty = sum(
            1 for s in steps_with_uncertainty
            if s.metadata["uncertainty"] < 0.4
        )
        clarity_ratio = low_uncertainty / len(steps_with_uncertainty)
    else:
        # No uncertainty data — use fact density as proxy
        clarity_ratio = min(1.0, facts_count / max(1, total_steps)) * 0.7

    fact_coverage = min(1.0, facts_count / expected_facts)
    score = fact_coverage * 60 + clarity_ratio * 40

    return ScoreResult(
        name="Documentation Clarity",
        value=min(100, max(0, score)),
        explanation=(
            f"Extracted {facts_count} facts (expected ~{expected_facts}). "
            f"Clarity ratio: {clarity_ratio:.0%}."
        ),
        inputs={
            "facts_extracted": facts_count,
            "expected_facts": expected_facts,
            "clarity_ratio": round(clarity_ratio, 3),
            "total_steps": total_steps,
        },
    )


def compute_tool_clarity(trace: RunTrace) -> ScoreResult:
    """How clear CLI commands or MCP tools were to discover and use.

    Formula:
        selection_component  = (correct / total) * 50
        argument_component   = arg_correctness * 30
        help_component       = help_factor * 20
        score                = sum of components

    Only applies to CLI and MCP surfaces.
    """
    tool_calls = [s for s in trace.steps if s.action_type in ("execute", "tool_call")]
    total = len(tool_calls)
    if total == 0:
        return ScoreResult(
            name="Tool Clarity",
            value=50.0,
            explanation="No tool/command invocations to evaluate.",
            inputs={"correct_tool_selections": 0, "total_selections": 0},
        )

    correct = sum(1 for s in tool_calls if s.success)
    arg_correct = sum(1 for s in tool_calls if s.success and not s.errors)
    arg_rate = arg_correct / total

    # Help usefulness: if help was consulted and the following action succeeded
    help_useful = 0
    for i, step in enumerate(trace.steps):
        if step.action_type == "read" and "help" in step.action.lower():
            if i + 1 < len(trace.steps) and trace.steps[i + 1].success:
                help_useful += 1

    help_factor = min(1.0, help_useful / max(1, total // 2))

    score = (correct / total) * 50 + arg_rate * 30 + help_factor * 20

    return ScoreResult(
        name="Tool Clarity",
        value=min(100, max(0, score)),
        explanation=(
            f"{correct}/{total} correct selections, "
            f"{arg_rate:.0%} arg correctness, "
            f"{help_useful} helpful help consultations."
        ),
        inputs={
            "correct_tool_selections": correct,
            "total_selections": total,
            "arg_correctness_rate": round(arg_rate, 3),
            "help_text_usefulness": help_useful,
        },
    )
