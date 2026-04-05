# ruff: noqa: E501 — prompt strings are naturally long
"""LLM-powered trace analysis.

After a run completes, this module sends the full trace to the LLM
and asks it to produce specific, actionable analysis based on what
actually happened — not templates.
"""

from __future__ import annotations

import json
import logging

from agentux.core.config import AgentUXConfig
from agentux.core.models import AffordanceStatus, RunTrace

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an expert in agent usability analysis. You just observed an AI agent attempting to use a {surface_type}.

TARGET: {target}
TASK: {task}
RESULT: {result} in {steps} steps ({duration})

Here is the complete step-by-step trace of what the agent did:

{trace_summary}

AFFORDANCES ON THIS SURFACE:
{affordance_summary}

SCORING SUMMARY:
{score_summary}

Based on this SPECIFIC run, produce analysis in EXACTLY this JSON format:
{{
  "observations": [
    "specific factual observation about what happened in this run"
  ],
  "insights": [
    "specific inference about WHY something happened, based on the trace"
  ],
  "recommendations": [
    "specific, actionable change the surface BUILDER should make"
  ]
}}

RULES:
1. Every point must reference SPECIFIC things from the trace — page names, commands, error messages, step numbers.
2. Observations are FACTS: what the agent did, what it found, what failed.
3. Insights are INFERENCES: why the agent got stuck, why it repeated itself, why it missed something.
4. Recommendations are for the BUILDER of the {surface_type}, not the person running the test. Tell them what to change about their {surface_type_noun} to make it more agent-friendly.
5. Be extremely specific. Not "improve navigation" but "move the pricing link from the footer dropdown to the main nav bar" (if that's what the trace shows).
6. 3-5 points per section. Quality over quantity.
7. If the run was too short to analyze meaningfully, say so honestly.

Respond with valid JSON only."""

SURFACE_NOUNS = {
    "browser": "website",
    "markdown": "documentation",
    "cli": "CLI tool",
    "mcp": "MCP server / tool definitions",
}


def _build_trace_summary(trace: RunTrace) -> str:
    """Build a concise text summary of the run trace for LLM analysis."""
    lines = []
    for step in trace.steps:
        status = "OK" if step.success else "FAIL"
        line = f"Step {step.step_number} [{status}] {step.action_type}: {step.action}"
        if step.thought_summary:
            line += f"\n  Thought: {step.thought_summary}"
        if step.result:
            line += f"\n  Result: {step.result[:200]}"
        if step.extracted_facts:
            line += f"\n  Facts: {', '.join(step.extracted_facts[:3])}"
        if step.errors:
            line += f"\n  Errors: {', '.join(step.errors[:2])}"
        lines.append(line)
    return "\n\n".join(lines) if lines else "No steps executed."


def _build_affordance_summary(trace: RunTrace) -> str:
    """Summarize affordances by status."""
    interacted = [a for a in trace.affordances if a.status == AffordanceStatus.INTERACTED]
    discovered = [a for a in trace.affordances if a.status == AffordanceStatus.DISCOVERED]
    missed = [a for a in trace.affordances if a.status == AffordanceStatus.MISSED]

    lines = []
    if interacted:
        lines.append(
            f"INTERACTED ({len(interacted)}): {', '.join(a.name for a in interacted[:10])}"
        )
    if discovered:
        lines.append(
            f"SEEN BUT NOT USED ({len(discovered)}): {', '.join(a.name for a in discovered[:10])}"
        )
    if missed:
        lines.append(f"MISSED ({len(missed)}): {', '.join(a.name for a in missed[:10])}")
    return "\n".join(lines) if lines else "No affordances tracked."


def _build_score_summary(trace: RunTrace) -> str:
    """Summarize scores."""
    lines = []
    for _key, result in trace.scores.as_dict().items():
        lines.append(f"{result.name}: {result.value:.0f}/100 — {result.explanation}")
    return "\n".join(lines)


async def analyze_trace_with_llm(
    trace: RunTrace,
    config: AgentUXConfig,
) -> dict[str, list[str]]:
    """Send the completed trace to the LLM for intelligent analysis.

    Returns dict with keys: observations, insights, recommendations.
    Falls back to empty lists on failure.
    """
    if trace.step_count == 0:
        return {
            "observations": [f"Run failed before any steps: {trace.failure_reason or 'unknown'}"],
            "insights": ["Cannot analyze — no agent interaction occurred"],
            "recommendations": ["Fix the infrastructure issue and re-run"],
        }

    surface_type = trace.surface_type.value
    duration = f"{trace.total_latency_ms / 1000:.1f}s" if trace.total_latency_ms else "unknown"

    prompt_text = ANALYSIS_PROMPT.format(
        surface_type=surface_type,
        surface_type_noun=SURFACE_NOUNS.get(surface_type, "surface"),
        target=trace.target,
        task=trace.task,
        result="PASSED" if trace.success else "FAILED",
        steps=trace.step_count,
        duration=duration,
        trace_summary=_build_trace_summary(trace),
        affordance_summary=_build_affordance_summary(trace),
        score_summary=_build_score_summary(trace),
    )

    try:
        from agentux.core.runner import create_backend

        backend = create_backend(config.backend.name, config)

        # Use the backend's underlying client directly for a simple completion
        if hasattr(backend, "_get_client"):
            client = backend._get_client()
        else:
            logger.info("Backend doesn't support direct client access, skipping LLM analysis")
            return _fallback_analysis(trace)

        # Call the LLM
        if config.backend.name == "anthropic":
            response = await client.messages.create(
                model=config.backend.model,
                system="You are an expert agent usability analyst. Respond with valid JSON only.",
                messages=[{"role": "user", "content": prompt_text}],
                max_tokens=2000,
                temperature=0.3,
            )
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text
        else:
            # OpenAI-compatible
            response = await client.chat.completions.create(
                model=config.backend.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert agent usability analyst. Respond with JSON.",
                    },
                    {"role": "user", "content": prompt_text},
                ],
                max_tokens=2000,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"

        # Parse JSON response — handle markdown wrapping
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        data = json.loads(content.strip())

        result = {
            "observations": [str(o) for o in (data.get("observations") or [])],
            "insights": [str(i) for i in (data.get("insights") or [])],
            "recommendations": [str(r) for r in (data.get("recommendations") or [])],
        }

        await backend.close()
        return result

    except Exception as e:
        logger.warning(f"LLM analysis failed, using fallback: {e}")
        return _fallback_analysis(trace)


def _fallback_analysis(trace: RunTrace) -> dict[str, list[str]]:
    """Basic analysis when LLM is unavailable."""
    observations = [f"{trace.step_count} steps taken, {trace.total_tokens} tokens used"]
    insights = []
    recommendations = []

    total_aff = len([a for a in trace.affordances if a.relevant])
    interacted = len(
        [a for a in trace.affordances if a.relevant and a.status == AffordanceStatus.INTERACTED]
    )
    if total_aff > 0:
        observations.append(f"Agent interacted with {interacted}/{total_aff} affordances")

    if trace.step_count < 4:
        insights.append("Run was too short for deep analysis")
    if not trace.success:
        insights.append(f"Run failed: {trace.failure_reason or 'unknown'}")

    recommendations.append(
        "LLM analysis unavailable — re-run with a configured backend for detailed recommendations"
    )

    return {
        "observations": observations,
        "insights": insights or ["Run completed"],
        "recommendations": recommendations,
    }
