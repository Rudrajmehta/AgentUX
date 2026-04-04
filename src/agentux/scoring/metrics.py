"""Metric computation functions for scoring.

Design principles:
1. No free points — every metric starts at 0 and must be earned
2. Shallow runs are penalized — 1-step "done" doesn't get 100
3. Interaction depth matters — discovering without interacting is partial credit
4. Recommendations are always provided — scores are actionable, not just numbers
5. No hardcoded defaults — unmeasurable metrics return explicit "N/A" explanations
"""

from __future__ import annotations

from agentux.core.models import (
    AffordanceStatus,
    RunTrace,
    ScoreResult,
)


def compute_discoverability(trace: RunTrace) -> ScoreResult:
    """How easily the agent found relevant affordances.

    Components:
    - Coverage: what fraction of relevant affordances were found (0-50 pts)
    - Interaction depth: found AND interacted with, not just seen (0-25 pts)
    - Discovery speed: how early were key affordances found (0-15 pts)
    - Breadth: did the agent explore multiple affordance types (0-10 pts)
    """
    relevant = [a for a in trace.affordances if a.relevant]
    total_relevant = len(relevant)

    if total_relevant == 0:
        return ScoreResult(
            name="Discoverability",
            value=0.0,
            explanation="No relevant affordances found on this surface.",
            inputs={
                "total_relevant": 0,
                "recommendations": [
                    "Surface exposed no affordances to the agent — check selectors/structure"
                ],
            },
        )

    discovered = [
        a
        for a in relevant
        if a.status in (AffordanceStatus.DISCOVERED, AffordanceStatus.INTERACTED)
    ]
    interacted = [a for a in relevant if a.status == AffordanceStatus.INTERACTED]
    missed = [a for a in relevant if a.status == AffordanceStatus.MISSED]

    # Coverage: what fraction was found at all (0-50)
    coverage_ratio = len(discovered) / total_relevant
    coverage_pts = coverage_ratio * 50

    # Interaction depth: found AND used (0-25)
    interaction_ratio = len(interacted) / total_relevant
    interaction_pts = interaction_ratio * 25

    # Discovery speed (0-15)
    total_steps = len(trace.steps) or 1
    first_discovery_step = None
    for step in trace.steps:
        if step.affordances_discovered:
            first_discovery_step = step.step_number
            break
    if first_discovery_step is not None:
        speed_pts = max(0, 15 * (1 - (first_discovery_step - 1) / total_steps))
    else:
        speed_pts = 0

    # Breadth: variety of affordance types discovered (0-10)
    kinds_found = {a.kind for a in discovered}
    kinds_total = {a.kind for a in relevant}
    breadth_pts = (len(kinds_found) / max(len(kinds_total), 1)) * 10

    score = coverage_pts + interaction_pts + speed_pts + breadth_pts

    # Build recommendations
    recommendations: list[str] = []
    if missed:
        missed_names = [a.name for a in missed[:5]]
        recommendations.append(f"Missed affordances: {', '.join(missed_names)}")
    if interaction_ratio < 0.5:
        recommendations.append(
            f"Only {len(interacted)}/{total_relevant} affordances were interacted with — "
            "surface may be hard to act on after discovery"
        )
    if speed_pts < 5:
        recommendations.append(
            "Key affordances took many steps to find — improve information hierarchy"
        )

    return ScoreResult(
        name="Discoverability",
        value=min(100, max(0, score)),
        explanation=(
            f"{len(discovered)}/{total_relevant} found, "
            f"{len(interacted)} interacted, "
            f"first at step {first_discovery_step or 'N/A'}, "
            f"{len(kinds_found)} types."
        ),
        inputs={
            "discovered": len(discovered),
            "interacted": len(interacted),
            "missed": len(missed),
            "total_relevant": total_relevant,
            "first_discovery_step": first_discovery_step,
            "coverage_pts": round(coverage_pts, 1),
            "interaction_pts": round(interaction_pts, 1),
            "speed_pts": round(speed_pts, 1),
            "breadth_pts": round(breadth_pts, 1),
            "recommendations": recommendations,
        },
    )


def compute_actionability(trace: RunTrace) -> ScoreResult:
    """How effectively the surface supported correct execution.

    Components:
    - Success rate on actions (0-40 pts)
    - First-try success rate (0-25 pts)
    - Action diversity: did agent use multiple action types (0-15 pts)
    - Depth penalty: runs with 0-1 action steps can't score high (0-20 pts)
    """
    action_steps = [s for s in trace.steps if s.action_type not in ("read", "done", "")]
    total_actions = len(action_steps)

    recommendations: list[str] = []

    if total_actions == 0:
        recommendations.append(
            "Agent never took an action — task may have been too easy or agent quit early"
        )
        return ScoreResult(
            name="Actionability",
            value=0.0,
            explanation="No actions taken — cannot evaluate surface actionability.",
            inputs={"total_actions": 0, "recommendations": recommendations},
        )

    successful = sum(1 for s in action_steps if s.success)
    first_try = sum(1 for s in action_steps if s.success and not s.errors)
    success_rate = successful / total_actions
    first_try_rate = first_try / total_actions

    # Success rate (0-40)
    success_pts = success_rate * 40

    # First-try rate (0-25)
    first_try_pts = first_try_rate * 25

    # Action diversity (0-15)
    action_types = {s.action_type for s in action_steps}
    diversity_pts = min(15, len(action_types) * 5)

    # Depth: more actions tested = more confidence in the score (0-20)
    # 1 action = 5pts, 3+ actions = 20pts
    depth_pts = min(20, total_actions * 5)

    score = success_pts + first_try_pts + diversity_pts + depth_pts

    if success_rate < 0.7:
        recommendations.append(
            f"{total_actions - successful}/{total_actions} actions failed — surface has friction"
        )
    if first_try_rate < 0.5:
        recommendations.append("Most actions needed retries — improve labels/selectors/feedback")
    if total_actions <= 1:
        recommendations.append("Only 1 action tested — score has low confidence")

    return ScoreResult(
        name="Actionability",
        value=min(100, max(0, score)),
        explanation=(
            f"{successful}/{total_actions} succeeded, "
            f"{first_try} first-try, "
            f"{len(action_types)} action types."
        ),
        inputs={
            "successful": successful,
            "total_actions": total_actions,
            "first_try": first_try,
            "action_types": sorted(action_types),
            "success_pts": round(success_pts, 1),
            "depth_pts": round(depth_pts, 1),
            "recommendations": recommendations,
        },
    )


def compute_recovery(trace: RunTrace) -> ScoreResult:
    """How well the surface helped the agent recover from errors.

    If no errors occurred, score is capped at 70 — we can't verify recovery
    capability without observing error handling.
    """
    errors_encountered = sum(1 for s in trace.steps if s.errors or not s.success)
    recommendations: list[str] = []

    if errors_encountered == 0:
        recommendations.append(
            "No errors occurred — recovery capability is untested. "
            "Score capped at 70 (would need error scenarios to verify)."
        )
        return ScoreResult(
            name="Recovery",
            value=70.0,
            explanation="No errors encountered — recovery untested (capped at 70).",
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

    # Base: 100, subtract for problems, add for recoveries
    score = max(0, 100 - (dead_ends * 15) - (unrecoverable * 25) + (recovered * 10))

    if dead_ends > 0:
        recommendations.append(
            f"{dead_ends} dead ends — add clearer error messages or fallback paths"
        )
    if unrecoverable > 0:
        recommendations.append(
            f"{unrecoverable} unrecoverable error chains — surface lacks recovery guidance"
        )
    if recovered > 0 and recovered >= dead_ends:
        recommendations.append("Good recovery rate — error messages appear helpful")

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
    """How much unnecessary effort was required.

    Penalty-based: starts at 100, loses points for waste.
    Also penalizes extremely short runs (1 step = capped at 60).
    """
    total_steps = len(trace.steps)
    recommendations: list[str] = []

    if total_steps == 0:
        return ScoreResult(
            name="Efficiency",
            value=0.0,
            explanation="No steps — cannot evaluate.",
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

    penalty = (backtracks * 12) + (redundant_reads * 5) + (wasted * 5)
    if total_steps > 10:
        penalty += (total_steps - 10) * 3

    score = max(0, 100 - penalty)

    # Cap score for very short runs — 1 step can't prove efficiency
    if total_steps <= 2:
        score = min(score, 60)
        recommendations.append(
            f"Only {total_steps} step(s) — efficiency score capped at 60 (insufficient depth)"
        )

    if backtracks > 0:
        recommendations.append(f"{backtracks} backtracks — navigation structure may be confusing")
    if redundant_reads > 0:
        recommendations.append(f"{redundant_reads} redundant reads — content may be hard to parse")
    if total_steps > 15:
        recommendations.append(f"{total_steps} steps — task may be too complex or surface too deep")

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
    """How clear and extractable the surface's information was.

    Components:
    - Fact density: unique facts extracted per step (0-40 pts)
    - Clarity: low uncertainty across steps (0-30 pts)
    - Depth penalty: 1-step runs capped (0-30 pts for depth)
    """
    all_facts: list[str] = []
    for step in trace.steps:
        all_facts.extend(step.extracted_facts)

    # Deduplicate facts (case-insensitive)
    unique_facts = list({f.lower().strip(): f for f in all_facts}.values())
    facts_count = len(unique_facts)
    total_steps = len(trace.steps) or 1
    recommendations: list[str] = []

    if total_steps == 0:
        return ScoreResult(
            name="Documentation Clarity",
            value=0.0,
            explanation="No steps — cannot evaluate.",
            inputs={"facts": 0, "recommendations": ["No steps executed"]},
        )

    # Fact density: facts per step, capped at 2 per step = full marks (0-40)
    fact_density = facts_count / total_steps
    fact_pts = min(40, fact_density * 20)

    # Clarity from uncertainty data (0-30)
    steps_with_uncertainty = [s for s in trace.steps if "uncertainty" in s.metadata]
    if steps_with_uncertainty:
        low_unc = sum(1 for s in steps_with_uncertainty if s.metadata["uncertainty"] < 0.4)
        clarity_ratio = low_unc / len(steps_with_uncertainty)
    else:
        clarity_ratio = 0.5  # No data = assume mediocre
    clarity_pts = clarity_ratio * 30

    # Depth: more steps explored = higher confidence (0-30)
    # 1 step = 10, 3 steps = 20, 5+ steps = 30
    depth_pts = min(30, total_steps * 6)

    score = fact_pts + clarity_pts + depth_pts

    if facts_count == 0:
        recommendations.append(
            "No facts extracted — content may be unclear or agent couldn't parse it"
        )
    if fact_density < 0.5:
        recommendations.append("Low fact density — many steps produced no useful information")
    if clarity_ratio < 0.5 and steps_with_uncertainty:
        recommendations.append("High uncertainty — surface information is ambiguous")
    if total_steps <= 2:
        recommendations.append("Shallow evaluation — depth limits scoring confidence")

    return ScoreResult(
        name="Documentation Clarity",
        value=min(100, max(0, score)),
        explanation=(
            f"{facts_count} unique facts in {total_steps} steps "
            f"({fact_density:.1f}/step). Clarity: {clarity_ratio:.0%}."
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
    """How clear CLI commands or MCP tools were to discover and use."""
    tool_calls = [s for s in trace.steps if s.action_type in ("execute", "tool_call")]
    total = len(tool_calls)
    recommendations: list[str] = []

    if total == 0:
        recommendations.append("No tools/commands invoked — cannot assess tool clarity")
        return ScoreResult(
            name="Tool Clarity",
            value=0.0,
            explanation="No tool invocations to evaluate.",
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

    if correct < total:
        recommendations.append(
            f"{total - correct}/{total} tool calls failed — improve schemas/descriptions"
        )
    if arg_rate < 0.7:
        recommendations.append("Low argument correctness — tool parameters may be unclear")

    return ScoreResult(
        name="Tool Clarity",
        value=min(100, max(0, score)),
        explanation=(
            f"{correct}/{total} correct, {arg_rate:.0%} args, {help_useful} help assists."
        ),
        inputs={
            "correct": correct,
            "total": total,
            "arg_rate": round(arg_rate, 2),
            "help_useful": help_useful,
            "recommendations": recommendations,
        },
    )
