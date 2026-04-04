"""Tests for the scoring engine and individual metrics."""

from __future__ import annotations

import pytest

from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
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
    def test_all_discovered_and_interacted(self, sample_trace: RunTrace) -> None:
        """When every relevant affordance is interacted, score is high."""
        for aff in sample_trace.affordances:
            if aff.relevant:
                aff.status = AffordanceStatus.INTERACTED
        result = compute_discoverability(sample_trace)
        assert result.value >= 75.0
        assert result.name == "Discoverability"

    def test_none_discovered(self) -> None:
        """All relevant affordances missed gives near-zero score."""
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[StepRecord(step_number=1, action="noop", action_type="read")],
            affordances=[
                Affordance(name="a", relevant=True, status=AffordanceStatus.MISSED),
                Affordance(name="b", relevant=True, status=AffordanceStatus.MISSED),
            ],
        )
        result = compute_discoverability(trace)
        assert result.value < 20.0

    def test_early_discovery_bonus(self) -> None:
        """Discovering affordances on step 1 gives a speed bonus."""
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[
                StepRecord(
                    step_number=1, action="a", action_type="read", affordances_discovered=["nav"]
                ),
                StepRecord(step_number=2, action="b", action_type="click"),
                StepRecord(step_number=3, action="c", action_type="done"),
            ],
            affordances=[
                Affordance(name="nav", relevant=True, status=AffordanceStatus.DISCOVERED),
            ],
        )
        result = compute_discoverability(trace)
        # Coverage (50) + speed bonus (15) = at least 60
        assert result.value >= 60.0

    def test_discovered_but_not_interacted_scores_lower(self) -> None:
        """Discovering without interacting gives partial credit."""
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[
                StepRecord(
                    step_number=1, action="a", action_type="read", affordances_discovered=["x"]
                )
            ],
            affordances=[
                Affordance(name="nav", relevant=True, status=AffordanceStatus.DISCOVERED),
                Affordance(name="cta", relevant=True, status=AffordanceStatus.DISCOVERED),
            ],
        )
        result_disc = compute_discoverability(trace)

        trace2 = RunTrace(
            run_id="y",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[
                StepRecord(
                    step_number=1, action="a", action_type="read", affordances_discovered=["x"]
                )
            ],
            affordances=[
                Affordance(name="nav", relevant=True, status=AffordanceStatus.INTERACTED),
                Affordance(name="cta", relevant=True, status=AffordanceStatus.INTERACTED),
            ],
        )
        result_inter = compute_discoverability(trace2)
        assert result_inter.value > result_disc.value

    def test_no_affordances(self) -> None:
        """Surface with no affordances scores 0."""
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[StepRecord(step_number=1, action="a", action_type="read")],
        )
        result = compute_discoverability(trace)
        assert result.value == 0.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_discoverability(empty_trace)
        assert 0 <= result.value <= 100


# ── Actionability ───────────────────────────────────────────────────────────


class TestActionability:
    def test_all_successful(self, sample_trace: RunTrace) -> None:
        result = compute_actionability(sample_trace)
        assert result.value > 40.0
        assert "succeeded" in result.explanation

    def test_all_failed(self, failed_trace: RunTrace) -> None:
        result = compute_actionability(failed_trace)
        # Depth + diversity points awarded, but success/first-try = 0
        assert result.value <= 30.0

    def test_no_actions_scores_zero(self) -> None:
        """Read-only run with no actions gets 0, not 50."""
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[
                StepRecord(step_number=1, action="a", action_type="read"),
                StepRecord(step_number=2, action="done", action_type="done"),
            ],
        )
        result = compute_actionability(trace)
        assert result.value == 0.0

    def test_mixed_results(self) -> None:
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=[
                StepRecord(step_number=1, action="a", action_type="click", success=True),
                StepRecord(
                    step_number=2,
                    action="b",
                    action_type="click",
                    success=False,
                    errors=["not found"],
                ),
                StepRecord(step_number=3, action="c", action_type="execute", success=True),
            ],
        )
        result = compute_actionability(trace)
        assert 30.0 < result.value < 90.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_actionability(empty_trace)
        assert 0 <= result.value <= 100


# ── Recovery ────────────────────────────────────────────────────────────────


class TestRecovery:
    def test_no_errors_capped(self, sample_trace: RunTrace) -> None:
        """No errors = recovery untested, capped at 70."""
        result = compute_recovery(sample_trace)
        assert result.value == 70.0

    def test_dead_ends(self) -> None:
        steps = [
            StepRecord(
                step_number=1, action="a", action_type="click", success=False, errors=["404"]
            ),
            StepRecord(
                step_number=2, action="b", action_type="click", success=False, errors=["timeout"]
            ),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_recovery(trace)
        assert result.value < 80.0

    def test_consecutive_failures_unrecoverable(self) -> None:
        steps = [
            StepRecord(
                step_number=i, action="a", action_type="click", success=False, errors=["fail"]
            )
            for i in range(1, 5)
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_recovery(trace)
        assert result.value < 50.0

    def test_helpful_error_recovery(self) -> None:
        steps = [
            StepRecord(
                step_number=1,
                action="a",
                action_type="click",
                success=False,
                errors=["Try --force"],
            ),
            StepRecord(step_number=2, action="b", action_type="click", success=True),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_recovery(trace)
        assert result.value >= 80.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        """Empty trace with no errors = recovery untested = 70."""
        result = compute_recovery(empty_trace)
        assert result.value == 70.0


# ── Efficiency ──────────────────────────────────────────────────────────────


class TestEfficiency:
    def test_minimal_steps_capped(self) -> None:
        """1-2 step runs are capped at 60 — insufficient depth."""
        steps = [
            StepRecord(step_number=1, action="a", action_type="click"),
            StepRecord(step_number=2, action="done", action_type="done"),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_efficiency(trace)
        assert result.value <= 60.0

    def test_good_medium_run(self) -> None:
        """A clean 5-step run with no waste scores high."""
        steps = [
            StepRecord(step_number=i, action=f"act{i}", action_type="click", success=True)
            for i in range(1, 6)
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
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
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
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
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
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
            StepRecord(
                step_number=1,
                action="a",
                action_type="read",
                extracted_facts=["fact1", "fact2", "fact3"],
            ),
            StepRecord(
                step_number=2, action="b", action_type="read", extracted_facts=["fact4", "fact5"]
            ),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_documentation_clarity(trace)
        assert result.value > 50.0

    def test_no_facts_low_score(self) -> None:
        steps = [
            StepRecord(step_number=1, action="a", action_type="read"),
            StepRecord(step_number=2, action="b", action_type="read"),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.BROWSER,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_documentation_clarity(trace)
        assert result.value < 50.0

    def test_empty_trace(self, empty_trace: RunTrace) -> None:
        result = compute_documentation_clarity(empty_trace)
        assert 0 <= result.value <= 100


# ── Tool Clarity (CLI/MCP only) ────────────────────────────────────────────


class TestToolClarity:
    def test_all_correct(self, cli_trace: RunTrace) -> None:
        result = compute_tool_clarity(cli_trace)
        assert result.value > 50.0
        assert "correct" in result.explanation

    def test_no_tool_calls_scores_zero(self, empty_trace: RunTrace) -> None:
        """No tool calls = 0, not 50."""
        result = compute_tool_clarity(empty_trace)
        assert result.value == 0.0

    def test_failed_tool_calls(self) -> None:
        steps = [
            StepRecord(
                step_number=1,
                action="bad",
                action_type="execute",
                success=False,
                errors=["unknown"],
            ),
            StepRecord(
                step_number=2,
                action="bad2",
                action_type="tool_call",
                success=False,
                errors=["invalid"],
            ),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.CLI,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_tool_clarity(trace)
        assert result.value == 0.0

    def test_help_usefulness(self) -> None:
        steps = [
            StepRecord(step_number=1, action="help deploy", action_type="read"),
            StepRecord(step_number=2, action="deploy --prod", action_type="execute", success=True),
        ]
        trace = RunTrace(
            run_id="x",
            surface_type=SurfaceType.CLI,
            target="t",
            task="t",
            steps=steps,
        )
        result = compute_tool_clarity(trace)
        assert result.value > 50.0


# ── ScoringEngine (composite AES) ──────────────────────────────────────────


class TestScoringEngine:
    def test_browser_score_has_no_tool_clarity(
        self,
        engine: ScoringEngine,
        sample_trace: RunTrace,
    ) -> None:
        card = engine.score(sample_trace)
        assert card.tool_clarity is None
        assert card.aes.value > 0

    def test_cli_score_has_tool_clarity(
        self,
        engine: ScoringEngine,
        cli_trace: RunTrace,
    ) -> None:
        card = engine.score(cli_trace)
        assert card.tool_clarity is not None
        assert card.tool_clarity.value > 0

    def test_mcp_score_has_tool_clarity(
        self,
        engine: ScoringEngine,
        mcp_trace: RunTrace,
    ) -> None:
        card = engine.score(mcp_trace)
        assert card.tool_clarity is not None

    def test_aes_is_bounded(self, engine: ScoringEngine, sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        assert 0 <= card.aes.value <= 100

    def test_aes_weights_sum_to_1_browser(
        self,
        engine: ScoringEngine,
        sample_trace: RunTrace,
    ) -> None:
        card = engine.score(sample_trace)
        weights = card.aes.inputs.get("weights", {})
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_aes_weights_sum_to_1_cli(
        self,
        engine: ScoringEngine,
        cli_trace: RunTrace,
    ) -> None:
        card = engine.score(cli_trace)
        weights = card.aes.inputs.get("weights", {})
        assert abs(sum(weights.values()) - 1.0) < 1e-9

    def test_empty_trace_scores(self, engine: ScoringEngine, empty_trace: RunTrace) -> None:
        card = engine.score(empty_trace)
        assert 0 <= card.aes.value <= 100

    def test_failed_trace_low_scores(
        self,
        engine: ScoringEngine,
        failed_trace: RunTrace,
    ) -> None:
        card = engine.score(failed_trace)
        assert 0 <= card.aes.value <= 100
        assert card.actionability.value <= 30.0  # All failed, but depth/diversity pts

    def test_scorecard_has_recommendations(
        self,
        engine: ScoringEngine,
        sample_trace: RunTrace,
    ) -> None:
        """Each metric should include recommendations."""
        card = engine.score(sample_trace)
        for _key, result in card.as_dict().items():
            recs = result.inputs.get("recommendations", [])
            assert isinstance(recs, list)

    def test_scorecard_as_dict(self, engine: ScoringEngine, sample_trace: RunTrace) -> None:
        card = engine.score(sample_trace)
        d = card.as_dict()
        assert "discoverability" in d
        assert "aes" in d
        assert "tool_clarity" not in d

    def test_scorecard_as_dict_cli(self, engine: ScoringEngine, cli_trace: RunTrace) -> None:
        card = engine.score(cli_trace)
        d = card.as_dict()
        assert "tool_clarity" in d
