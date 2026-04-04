"""Score definitions with formulas, explanations, and interpretation guidance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreDefinition:
    name: str
    key: str
    description: str
    formula: str
    inputs: list[str]
    interpretation: str
    weight_in_aes: float
    applicable_surfaces: list[str]


DISCOVERABILITY = ScoreDefinition(
    name="Discoverability Score",
    key="discoverability",
    description=(
        "How easily the agent identified relevant sections, commands, or tools "
        "on the surface. A high score means the surface clearly exposes its "
        "affordances to an agent encountering it for the first time."
    ),
    formula=(
        "score = (discovered_relevant / total_relevant) * 80 "
        "+ (first_discovery_speed_factor) * 20"
    ),
    inputs=[
        "discovered_relevant: count of relevant affordances discovered",
        "total_relevant: total relevant affordances on the surface",
        "steps_to_first_discovery: steps before first relevant affordance found",
    ],
    interpretation=(
        "90-100: Excellent - affordances are immediately visible and clear\n"
        "70-89: Good - most affordances found without difficulty\n"
        "40-69: Fair - some affordances hard to find or ambiguous\n"
        "0-39: Poor - critical affordances hidden or unclear"
    ),
    weight_in_aes=0.20,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

ACTIONABILITY = ScoreDefinition(
    name="Actionability Score",
    key="actionability",
    description=(
        "How effectively the surface supported correct execution once the "
        "right affordance was discovered. Measures whether discovered elements "
        "can be acted upon without confusion."
    ),
    formula=(
        "score = (successful_actions / total_actions) * 70 "
        "+ (correct_on_first_try / total_actions) * 30"
    ),
    inputs=[
        "successful_actions: actions that produced expected results",
        "total_actions: total actions attempted",
        "correct_on_first_try: actions that succeeded without retry",
    ],
    interpretation=(
        "90-100: Excellent - actions work as expected with clear feedback\n"
        "70-89: Good - most actions succeed, minor friction\n"
        "40-69: Fair - frequent action failures or unclear feedback\n"
        "0-39: Poor - surface actively hinders correct action"
    ),
    weight_in_aes=0.20,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

RECOVERY = ScoreDefinition(
    name="Recovery Score",
    key="recovery",
    description=(
        "How well the surface helped the agent recover after confusion or error. "
        "Measures error messages, help availability, and backtrack ease."
    ),
    formula=(
        "score = 100 - (dead_ends * 15) - (unrecoverable_errors * 25) "
        "+ (helpful_error_messages * 10)"
    ),
    inputs=[
        "dead_ends: times the agent hit a dead end",
        "unrecoverable_errors: errors with no clear recovery path",
        "helpful_error_messages: errors that included actionable guidance",
    ],
    interpretation=(
        "90-100: Excellent - clear error recovery paths\n"
        "70-89: Good - most errors recoverable\n"
        "40-69: Fair - some dead ends without guidance\n"
        "0-39: Poor - errors are opaque, recovery is difficult"
    ),
    weight_in_aes=0.15,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

EFFICIENCY = ScoreDefinition(
    name="Efficiency Score",
    key="efficiency",
    description=(
        "How much unnecessary navigation, retries, or extra context was required. "
        "A perfect score means the agent completed the task in minimal steps."
    ),
    formula=(
        "score = max(0, 100 - (excess_steps * 8) - (backtracks * 12) "
        "- (redundant_reads * 5))"
    ),
    inputs=[
        "actual_steps: steps taken to complete task",
        "optimal_steps: estimated minimum steps needed",
        "backtracks: times the agent reversed direction",
        "redundant_reads: times the agent re-read same content",
    ],
    interpretation=(
        "90-100: Excellent - near-optimal path\n"
        "70-89: Good - minor inefficiencies\n"
        "40-69: Fair - significant wasted effort\n"
        "0-39: Poor - excessive wandering or retries"
    ),
    weight_in_aes=0.15,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

DOCUMENTATION_CLARITY = ScoreDefinition(
    name="Documentation Clarity Score",
    key="documentation_clarity",
    description=(
        "How clear the information structure and explanatory content were. "
        "Measures whether the surface provides enough context for an agent "
        "to understand what it's looking at."
    ),
    formula=(
        "score = (facts_extracted / expected_facts) * 60 "
        "+ (low_uncertainty_steps / total_steps) * 40"
    ),
    inputs=[
        "facts_extracted: useful facts the agent could extract",
        "expected_facts: facts needed to complete the task",
        "low_uncertainty_steps: steps where agent had low uncertainty",
        "total_steps: total steps in the run",
    ],
    interpretation=(
        "90-100: Excellent - information is clear and well-structured\n"
        "70-89: Good - mostly clear with minor gaps\n"
        "40-69: Fair - important information unclear or missing\n"
        "0-39: Poor - content is confusing or misleading"
    ),
    weight_in_aes=0.15,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

TOOL_CLARITY = ScoreDefinition(
    name="Tool Clarity Score",
    key="tool_clarity",
    description=(
        "For CLI and MCP surfaces: how clear command/tool names, flags, "
        "descriptions, and examples were. Measures schema and help quality."
    ),
    formula=(
        "score = (correct_tool_selections / total_selections) * 50 "
        "+ (arg_correctness_rate) * 30 "
        "+ (help_text_usefulness) * 20"
    ),
    inputs=[
        "correct_tool_selections: times the right tool/command was chosen",
        "total_selections: total tool/command selection attempts",
        "arg_correctness_rate: rate of correct argument formation",
        "help_text_usefulness: whether help text aided correct usage",
    ],
    interpretation=(
        "90-100: Excellent - tools are self-documenting\n"
        "70-89: Good - minor naming or schema issues\n"
        "40-69: Fair - confusing names or missing descriptions\n"
        "0-39: Poor - tools are undiscoverable or misleading"
    ),
    weight_in_aes=0.15,
    applicable_surfaces=["cli", "mcp"],
)

AES = ScoreDefinition(
    name="Agent Efficacy Score (AES)",
    key="aes",
    description=(
        "A composite score summarizing overall first-run usability for the agent. "
        "Weighted combination of all component scores, surface-aware."
    ),
    formula=(
        "For browser/markdown: "
        "aes = disc*0.25 + act*0.25 + rec*0.15 + eff*0.15 + doc*0.20\n"
        "For cli/mcp: "
        "aes = disc*0.20 + act*0.20 + rec*0.15 + eff*0.15 + doc*0.15 + tool*0.15"
    ),
    inputs=["All component scores"],
    interpretation=(
        "90-100: Excellent agent usability\n"
        "70-89: Good - usable with minor friction\n"
        "40-69: Fair - agent struggles significantly\n"
        "0-39: Poor - surface is effectively unusable for agents"
    ),
    weight_in_aes=1.0,
    applicable_surfaces=["browser", "markdown", "cli", "mcp"],
)

ALL_DEFINITIONS = [
    DISCOVERABILITY,
    ACTIONABILITY,
    RECOVERY,
    EFFICIENCY,
    DOCUMENTATION_CLARITY,
    TOOL_CLARITY,
    AES,
]


def get_definition(key: str) -> ScoreDefinition | None:
    for d in ALL_DEFINITIONS:
        if d.key == key:
            return d
    return None
