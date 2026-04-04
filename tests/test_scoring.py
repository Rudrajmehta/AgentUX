"""Tests for the scoring engine and individual metrics."""

from __future__ import annotations

import pytest

from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
    ScoreCard,
    ScoreResult,
    StepRecord,
    SurfaceType,
)
from agentux.scoring.engine import ScoringEngine
from agentux.scoring.metrics import (
    compute_actionability,
    compute_discoverability,
    compute_documentation_clarity,
    compute_efficiency,
    compute_recovery,
    compute_tool_clarity,
)


@pytest.fixture
def engine() -> ScoringEngine:
    return ScoringEngine()


# ── Discoverability ─────────────────────────────────────────────────────────

class TestDiscoverability:
    def test_all_discovered(self, sample_trace: RunTrace) -> None:
        """When every relevant affordance is discovered/interacted, coverage is high."""
        # Make all relevant affordances discovered
        for aff in sample_trace.affordances:
            if aff.relevant:
                aff.status = AffordanceStatus.INTERACTED
        result = compute_discoverability(sample_trace)
        assert result.value >= 80.0
        assert result.name == "Discoverability"

    def test_none_discovered(self) -> None:
        """All relevant affordances missed gives low score."""
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t",
            steps=[StepRecord(step_number=1, action="noop", action_type="read")],
            affordances=[
                Affordance(name="a", relevant=True, status=AffordanceStatus.MISSED),
                Affordance(name="b", relevant=True, status=AffordanceStatus.MISSED),
            ],
        )
        result = compute_discoverability(trace)
        # Coverage is 0, so score comes only from speed factor
        assert result.value < 30.0

    def test_early_discovery_bonus(self) -> None:
        """Discovering affordances on step 1 gives a speed bonus."""
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t",
            steps=[
                StepRecord(step_number=1, action="a", action_type="read",
                           affordances_discovered=["nav"]),
                StepRecord(step_number=2, action="b", action_type="click"),
                StepRecord(step_number=3, action="c", action_type="done"),
            ],
            affordances=[
                Affordance(name="nav", relevant=True, status=AffordanceStatus.DISCOVERED),
            ],
        )
        result = compute_discoverability(trace)
        # Full coverage (80) + speed bonus
        assert result.value > 80.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_discoverability(empty_trace)
        assert 0 <= result.value <= 100


# ── Actionability ───────────────────────────────────────────────────────────

class TestActionability:
    def test_all_successful(self, sample_trace: RunTrace) -> None:
        result = compute_actionability(sample_trace)
        assert result.value > 50.0
        assert "succeeded" in result.explanation

    def test_all_failed(self, failed_trace: RunTrace) -> None:
        result = compute_actionability(failed_trace)
        assert result.value == 0.0

    def test_mixed_results(self) -> None:
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t",
            steps=[
                StepRecord(step_number=1, action="a", action_type="click", success=True),
                StepRecord(step_number=2, action="b", action_type="click",
                           success=False, errors=["not found"]),
                StepRecord(step_number=3, action="c", action_type="execute", success=True),
            ],
        )
        result = compute_actionability(trace)
        # 2/3 successful = ~66% base, plus first-try factor
        assert 40.0 < result.value < 90.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_actionability(empty_trace)
        assert 0 <= result.value <= 100


# ── Recovery ────────────────────────────────────────────────────────────────

class TestRecovery:
    def test_no_errors(self, sample_trace: RunTrace) -> None:
        result = compute_recovery(sample_trace)
        assert result.value == 100.0

    def test_dead_ends(self) -> None:
        steps = [
            StepRecord(step_number=1, action="a", action_type="click",
                       success=False, errors=["404"]),
            StepRecord(step_number=2, action="b", action_type="click",
                       success=False, errors=["timeout"]),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_recovery(trace)
        assert result.value < 100.0

    def test_consecutive_failures_unrecoverable(self) -> None:
        """Three consecutive failures count as unrecoverable."""
        steps = [
            StepRecord(step_number=i, action="a", action_type="click",
                       success=False, errors=["fail"])
            for i in range(1, 5)
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_recovery(trace)
        assert result.value < 50.0

    def test_helpful_error_recovery(self) -> None:
        """Error followed by a successful step gets helpful-error credit."""
        steps = [
            StepRecord(step_number=1, action="a", action_type="click",
                       success=False, errors=["Try --force"]),
            StepRecord(step_number=2, action="b", action_type="click", success=True),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_recovery(trace)
        # helpful_errors offsets some dead-end penalty
        assert result.value >= 80.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_recovery(empty_trace)
        assert result.value == 100.0


# ── Efficiency ──────────────────────────────────────────────────────────────

class TestEfficiency:
    def test_minimal_steps(self) -> None:
        """Very few steps should score high."""
        steps = [
            StepRecord(step_number=1, action="a", action_type="click"),
            StepRecord(step_number=2, action="done", action_type="done"),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_efficiency(trace)
        assert result.value >= 90.0

    def test_many_backtracks_lowers_score(self) -> None:
        steps = [
            StepRecord(step_number=1, action="a", action_type="click"),
            StepRecord(step_number=2, action="back", action_type="back"),
            StepRecord(step_number=3, action="b", action_type="click"),
            StepRecord(step_number=4, action="back", action_type="back"),
            StepRecord(step_number=5, action="c", action_type="click"),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_efficiency(trace)
        assert result.value < 80.0

    def test_redundant_reads(self) -> None:
        steps = [
            StepRecord(step_number=1, action="read_page", action_type="read"),
            StepRecord(step_number=2, action="read_page", action_type="read"),
            StepRecord(step_number=3, action="read_page", action_type="read"),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_efficiency(trace)
        assert result.value < 100.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_efficiency(empty_trace)
        assert 0 <= result.value <= 100


# ── Documentation Clarity ───────────────────────────────────────────────────

class TestDocumentationClarity:
    def test_many_facts_high_score(self) -> None:
        steps = [
            StepRecord(step_number=1, action="a", action_type="read",
                       extracted_facts=["fact1", "fact2", "fact3"]),
            StepRecord(step_number=2, action="b", action_type="read",
                       extracted_facts=["fact4", "fact5"]),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_documentation_clarity(trace)
        assert result.value > 50.0

    def test_no_facts_low_score(self) -> None:
        steps = [
            StepRecord(step_number=1, action="a", action_type="read"),
            StepRecord(step_number=2, action="b", action_type="read"),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.BROWSER,
            target="t", task="t", steps=steps,
        )
        result = compute_documentation_clarity(trace)
        assert result.value < 80.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_documentation_clarity(empty_trace)
        assert 0 <= result.value <= 100


# ── Tool Clarity (CLI/MCP only) ────────────────────────────────────────────

class TestToolClarity:
    def test_all_correct(self, cli_trace: RunTrace) -> None:
        result = compute_tool_clarity(cli_trace)
        assert result.value > 50.0
        assert "correct selections" in result.explanation

    def test_no_tool_calls(self, empty_trace: RunTrace) -> None:
        result = compute_tool_clarity(empty_trace)
        assert 0 <= result.value <= 100

    def test_failed_tool_calls(self) -> None:
        steps = [
            StepRecord(step_number=1, action="bad_cmd", action_type="execute",
                       success=False, errors=["unknown command"]),
            StepRecord(step_number=2, action="bad_cmd2", action_type="tool_call",
                       success=False, errors=["invalid args"]),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.CLI,
            target="t", task="t", steps=steps,
        )
        result = compute_tool_clarity(trace)
        assert result.value == 0.0

    def test_help_usefulness(self) -> None:
        """Help consultation followed by success boosts score."""
        steps = [
            StepRecord(step_number=1, action="help deploy", action_type="read"),
            StepRecord(step_number=2, action="deploy --prod", action_type="execute",
                       success=True),
        ]
        trace = RunTrace(
            run_id="x", surface_type=SurfaceType.CLI,
            target="t", task="t", steps=steps,
        )
        result = compute_tool_clarity(trace)
        assert result.value > 50.0


# ── ScoringEngine (composite AES) ──────────────────────────────────────────

class TestScoringEngine:
    def test_browser_score_has_no_tool_clarity(self, engine: ScoringEngine,
                                                sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        assert card.tool_clarity is None
        assert card.aes.value > 0

    def test_cli_score_has_tool_clarity(self, engine: ScoringEngine,
                                        cli_trace: RunTrace) -> None:
        card = engine.score(cli_trace)
        assert card.tool_clarity is not None
        assert card.tool_clarity.value > 0

    def test_mcp_score_has_tool_clarity(self, engine: ScoringEngine,
                                        mcp_trace: RunTrace) -> None:
        card = engine.score(mcp_trace)
        assert card.tool_clarity is not None

    def test_aes_is_bounded(self, engine: ScoringEngine, sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        assert 0 <= card.aes.value <= 100

    def test_aes_weights_sum_to_1_browser(self, engine: ScoringEngine,
                                           sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        weights = card.aes.inputs.get("weights", {})
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_aes_weights_sum_to_1_cli(self, engine: ScoringEngine,
                                       cli_trace: RunTrace) -> None:
        card = engine.score(cli_trace)
        weights = card.aes.inputs.get("weights", {})
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_empty_trace_scores(self, engine: ScoringEngine, empty_trace: RunTrace) -> None:
        card = engine.score(empty_trace)
        assert 0 <= card.aes.value <= 100

    def test_failed_trace_scores(self, engine: ScoringEngine, failed_trace: RunTrace) -> None:
        card = engine.score(failed_trace)
        # Should still produce valid scores, just lower
        assert 0 <= card.aes.value <= 100
        assert card.actionability.value == 0.0

    def test_scorecard_as_dict(self, engine: ScoringEngine,
                                sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        d = card.as_dict()
        assert "discoverability" in d
        assert "aes" in d
        # Browser has no tool_clarity
        assert "tool_clarity" not in d

    def test_scorecard_as_dict_cli(self, engine: ScoringEngine,
                                    cli_trace: RunTrace) -> None:
        card = engine.score(cli_trace)
        d = card.as_dict()
        assert "tool_clarity" in d
