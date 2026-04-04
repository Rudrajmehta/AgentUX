"""Metric computation functions for scoring.

Design principles:
1. Scores reflect what the AGENT actually did, not what exists on the surface
2. surface.discover() lists what's available — that's the denominator, not credit
3. Only INTERACTED affordances count as agent discovery
4. Shallow runs score low — you can't prove usability in 2 steps
5. Every score includes actionable recommendations
6. No score above 90 without thorough testing
"""

from __future__ import annotations

from agentux.core.models import (
    AffordanceStatus,
    RunTrace,
    ScoreResult,
)


def compute_discoverability(trace: RunTrace) -> ScoreResult:
    """What fraction of available affordances did the agent actually interact with?

    This measures the agent's REAL coverage, not what the surface listed.
    surface.discover() = total available. INTERACTED = what the agent actually touched.

    Score = (interacted / total_available) * 100, with bonuses/penalties.
    """
    all_affordances = trace.affordances
    total = len(all_affordances)
    relevant = [a for a in all_affordances if a.relevant]
    total_relevant = len(relevant) or total or 1

    # INTERACTED = agent actually used it. This is the real metric.
    interacted = [a for a in relevant if a.status == AffordanceStatus.INTERACTED]
    interaction_rate = len(interacted) / total_relevant

    recommendations: list[str] = []

    if total == 0:
        return ScoreResult(
            name="Discoverability",
            value=0.0,
            explanation="No affordances on this surface.",
            inputs={"recommendations": ["Surface has no discoverable elements"]},
        )

    # Base score: interaction rate (0-100)
    score = interaction_rate * 100

    # Penalty: if agent only touched <20% of available affordances, cap at 40
    if interaction_rate < 0.2 and total_relevant > 3:
        score = min(score, 40)
        not_touched = total_relevant - len(interacted)
        recommendations.append(
            f"Agent only interacted with {len(interacted)}/{total_relevant} "
            f"available affordances ({interaction_rate:.0%}) — {not_touched} untested"
        )

    # Bonus: early discovery (first interaction in step 1-2)
    first_interaction_step = None
    for step in trace.steps:
        if step.affordances_discovered:
            first_interaction_step = step.step_number
            break
    if first_interaction_step and first_interaction_step <= 2:
        score = min(100, score + 5)

    # List what was missed
    missed_relevant = [a for a in relevant if a.status != AffordanceStatus.INTERACTED]
    if missed_relevant and len(missed_relevant) > 2:
        names = [a.name for a in missed_relevant[:5]]
        recommendations.append(f"Not tested: {', '.join(names)}")

    return ScoreResult(
        name="Discoverability",
        value=min(100, max(0, score)),
        explanation=(
            f"Agent interacted with {len(interacted)}/{total_relevant} "
            f"affordances ({interaction_rate:.0%})."
        ),
        inputs={
            "interacted": len(interacted),
            "total_relevant": total_relevant,
            "interaction_rate": round(interaction_rate, 3),
            "first_interaction_step": first_interaction_step,
            "recommendations": recommendations,
        },
    )


def compute_actionability(trace: RunTrace) -> ScoreResult:
    """Of the actions the agent attempted, how many worked?

    Components:
    - Success rate (0-50): what fraction succeeded
    - First-try rate (0-25): succeeded without errors
    - Sample penalty: <3 actions → score capped at 60
    """
    action_steps = [s for s in trace.steps if s.action_type not in ("read", "done", "")]
    total_actions = len(action_steps)
    recommendations: list[str] = []

    if total_actions == 0:
        recommendations.append(
            "Agent took no actions (only reads/done) — cannot evaluate surface actionability"
        )
        return ScoreResult(
            name="Actionability",
            value=0.0,
            explanation="No actions attempted.",
            inputs={"total_actions": 0, "recommendations": recommendations},
        )

    successful = sum(1 for s in action_steps if s.success)
    first_try = sum(1 for s in action_steps if s.success and not s.errors)
    success_rate = successful / total_actions
    first_try_rate = first_try / total_actions

    # Score components
    success_pts = success_rate * 50
    first_try_pts = first_try_rate * 25
    score = success_pts + first_try_pts

    # Depth bonus: more actions tested = more confidence (up to +25)
    depth_bonus = min(25, total_actions * 5)
    score += depth_bonus

    # Sample penalty: <3 actions → cap at 60 (low confidence)
    if total_actions < 3:
        score = min(score, 60)
        recommendations.append(
            f"Only {total_actions} action(s) tested — low confidence score (capped at 60)"
        )

    if success_rate < 0.7:
        failed = total_actions - successful
        recommendations.append(f"{failed}/{total_actions} actions failed — surface has friction")
    if total_actions >= 3 and first_try_rate < 0.5:
        recommendations.append("Most actions needed retries — improve labels/feedback")

    return ScoreResult(
        name="Actionability",
        value=min(100, max(0, score)),
        explanation=f"{successful}/{total_actions} succeeded, {first_try} first-try.",
        inputs={
            "successful": successful,
            "total_actions": total_actions,
            "first_try": first_try,
            "success_rate": round(success_rate, 3),
            "depth_bonus": depth_bonus,
            "recommendations": recommendations,
        },
    )


def compute_recovery(trace: RunTrace) -> ScoreResult:
    """How well the surface helped the agent recover from errors.

    If no errors occurred, score is capped at 50 — recovery is completely untested.
    """
    errors_encountered = sum(1 for s in trace.steps if s.errors or not s.success)
    recommendations: list[str] = []

    if errors_encountered == 0:
        recommendations.append(
            "No errors occurred — recovery is completely untested. "
            "Score capped at 50. Run harder tasks to stress-test error handling."
        )
        return ScoreResult(
            name="Recovery",
            value=50.0,
            explanation="No errors — recovery untested (capped at 50).",
            inputs={"errors_encountered": 0, "recommendations": recommendations},
        )

    dead_ends = 0
    recovered = 0
    unrecoverable = 0

    for i, step in enumerate(trace.steps):
        if step.errors or not step.success:
            if i + 1 < len(trace.steps) and trace.steps[i + 1].success:
                recovered += 1
            else:
                dead_ends += 1
        if step.action_type == "back":
            dead_ends += 1

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

    if dead_ends > 0:
        recommendations.append(f"{dead_ends} dead ends — improve error messages and fallback paths")
    if unrecoverable > 0:
        recommendations.append(
            f"{unrecoverable} unrecoverable error chains — surface lacks recovery guidance"
        )

    return ScoreResult(
        name="Recovery",
        value=min(100, max(0, score)),
        explanation=(
            f"{errors_encountered} errors, {dead_ends} dead ends, "
            f"{recovered} recoveries, {unrecoverable} unrecoverable."
        ),
        inputs={
            "errors_encountered": errors_encountered,
            "dead_ends": dead_ends,
            "recovered": recovered,
            "unrecoverable": unrecoverable,
            "recommendations": recommendations,
        },
    )


def compute_efficiency(trace: RunTrace) -> ScoreResult:
    """Was the agent's path clean and purposeful?

    Penalties for: backtracks, redundant reads, wasted steps, excessive length.
    Cap for very short runs (< 3 steps = capped at 50).
    """
    total_steps = len(trace.steps)
    recommendations: list[str] = []

    if total_steps == 0:
        return ScoreResult(
            name="Efficiency",
            value=0.0,
            explanation="No steps.",
            inputs={"actual_steps": 0, "recommendations": ["Run had no steps"]},
        )

    backtracks = sum(1 for s in trace.steps if s.action_type == "back")

    redundant_reads = 0
    seen_actions: set[str] = set()
    for step in trace.steps:
        key = f"{step.action}:{step.action_type}"
        if key in seen_actions and step.action_type == "read":
            redundant_reads += 1
        seen_actions.add(key)

    wasted = 0
    for i, step in enumerate(trace.steps):
        if not step.success and i + 1 < len(trace.steps) and not trace.steps[i + 1].success:
            wasted += 1

    penalty = (backtracks * 12) + (redundant_reads * 8) + (wasted * 8)
    if total_steps > 10:
        penalty += (total_steps - 10) * 3

    score = max(0, 100 - penalty)

    # Short runs: can't prove efficiency in <3 steps — capped at 50
    if total_steps < 3:
        score = min(score, 50)
        recommendations.append(
            f"Only {total_steps} step(s) — too few to evaluate efficiency (capped at 50)"
        )

    if backtracks > 0:
        recommendations.append(f"{backtracks} backtracks — navigation may be confusing")
    if redundant_reads > 0:
        recommendations.append(f"{redundant_reads} redundant reads — content hard to parse")
    if total_steps > 15:
        recommendations.append(f"{total_steps} steps taken — task required excessive exploration")

    return ScoreResult(
        name="Efficiency",
        value=min(100, max(0, score)),
        explanation=(
            f"{total_steps} steps, {backtracks} backtracks, "
            f"{redundant_reads} redundant, {wasted} wasted."
        ),
        inputs={
            "actual_steps": total_steps,
            "backtracks": backtracks,
            "redundant_reads": redundant_reads,
            "wasted_steps": wasted,
            "penalty": penalty,
            "recommendations": recommendations,
        },
    )


def compute_documentation_clarity(trace: RunTrace) -> ScoreResult:
    """How much useful, unique information did the agent extract?

    Based on unique facts per step. Deduplicates facts.
    Short runs (<3 steps) capped at 50.
    """
    all_facts: list[str] = []
    for step in trace.steps:
        all_facts.extend(step.extracted_facts)

    unique_facts = list({f.lower().strip(): f for f in all_facts}.values())
    facts_count = len(unique_facts)
    total_steps = len(trace.steps) or 1
    recommendations: list[str] = []

    if total_steps == 0:
        return ScoreResult(
            name="Documentation Clarity",
            value=0.0,
            explanation="No steps.",
            inputs={"facts": 0, "recommendations": ["No steps executed"]},
        )

    # Fact density (0-50)
    fact_density = facts_count / total_steps
    fact_pts = min(50, fact_density * 25)

    # Clarity from uncertainty (0-25)
    steps_with_unc = [s for s in trace.steps if "uncertainty" in s.metadata]
    if steps_with_unc:
        low_unc = sum(1 for s in steps_with_unc if s.metadata["uncertainty"] < 0.4)
        clarity_ratio = low_unc / len(steps_with_unc)
    else:
        clarity_ratio = 0.5
    clarity_pts = clarity_ratio * 25

    # Depth (0-25)
    depth_pts = min(25, total_steps * 5)

    score = fact_pts + clarity_pts + depth_pts

    # Cap for shallow runs
    if total_steps < 3:
        score = min(score, 50)
        recommendations.append("Shallow run — too few steps for confident clarity score")

    if facts_count == 0:
        recommendations.append("No facts extracted — content may be unclear")
    if fact_density < 0.5:
        recommendations.append("Low fact density — many steps yielded no information")

    return ScoreResult(
        name="Documentation Clarity",
        value=min(100, max(0, score)),
        explanation=(
            f"{facts_count} unique facts in {total_steps} steps ({fact_density:.1f}/step)."
        ),
        inputs={
            "unique_facts": facts_count,
            "fact_density": round(fact_density, 2),
            "clarity_ratio": round(clarity_ratio, 2),
            "depth_pts": round(depth_pts, 1),
            "recommendations": recommendations,
        },
    )


def compute_tool_clarity(trace: RunTrace) -> ScoreResult:
    """How clear were CLI commands / MCP tools to use?

    Capped at 50 when <3 tool invocations (low confidence).
    """
    tool_calls = [s for s in trace.steps if s.action_type in ("execute", "tool_call")]
    total = len(tool_calls)
    recommendations: list[str] = []

    if total == 0:
        recommendations.append("No tools/commands invoked — cannot assess")
        return ScoreResult(
            name="Tool Clarity",
            value=0.0,
            explanation="No tool invocations.",
            inputs={"total_calls": 0, "recommendations": recommendations},
        )

    correct = sum(1 for s in tool_calls if s.success)
    arg_correct = sum(1 for s in tool_calls if s.success and not s.errors)
    arg_rate = arg_correct / total

    help_useful = 0
    for i, step in enumerate(trace.steps):
        if (
            step.action_type == "read"
            and "help" in step.action.lower()
            and i + 1 < len(trace.steps)
            and trace.steps[i + 1].success
        ):
            help_useful += 1

    help_factor = min(1.0, help_useful / max(1, total // 2))
    score = (correct / total) * 50 + arg_rate * 30 + help_factor * 20

    # Sample penalty
    if total < 3:
        score = min(score, 50)
        recommendations.append(f"Only {total} tool call(s) — low confidence (capped at 50)")

    if correct < total:
        recommendations.append(
            f"{total - correct}/{total} calls failed — improve schemas/descriptions"
        )

    return ScoreResult(
        name="Tool Clarity",
        value=min(100, max(0, score)),
        explanation=f"{correct}/{total} correct, {arg_rate:.0%} args, {help_useful} help assists.",
        inputs={
            "correct": correct,
            "total": total,
            "arg_rate": round(arg_rate, 2),
            "help_useful": help_useful,
            "recommendations": recommendations,
        },
    )
