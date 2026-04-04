"""Tests for analyzer pipeline."""

from agentux.analyzers.affordance import AffordanceAnalyzer
from agentux.analyzers.coverage import CoverageAnalyzer
from agentux.analyzers.friction import FrictionAnalyzer
from agentux.analyzers.pipeline import AnalyzerPipeline
from agentux.core.models import (
    Affordance,
    AffordanceStatus,
    RunTrace,
    StepRecord,
    SurfaceType,
)


def _make_trace() -> RunTrace:
    trace = RunTrace(
        surface_type=SurfaceType.BROWSER,
        target="https://example.com",
        task="test task",
    )
    trace.affordances = [
        Affordance(
            name="header", kind="section", status=AffordanceStatus.INTERACTED, relevant=True
        ),
        Affordance(
            name="pricing", kind="section", status=AffordanceStatus.DISCOVERED, relevant=True
        ),
        Affordance(name="footer", kind="section", status=AffordanceStatus.MISSED, relevant=False),
        Affordance(name="docs", kind="section", status=AffordanceStatus.MISSED, relevant=True),
    ]
    trace.add_step(StepRecord(step_number=1, action="click", action_type="click", success=True))
    trace.add_step(
        StepRecord(
            step_number=2, action="navigate", action_type="navigate", success=False, errors=["404"]
        )
    )
    trace.add_step(StepRecord(step_number=3, action="back", action_type="back", success=True))
    trace.add_step(
        StepRecord(
            step_number=4,
            action="click",
            action_type="click",
            success=True,
            extracted_facts=["found pricing"],
        )
    )
    return trace


def test_affordance_analyzer():
    trace = _make_trace()
    result = AffordanceAnalyzer().analyze(trace)
    assert result["relevant_total"] == 3
    assert result["relevant_found"] == 2
    assert len(result["missed"]) >= 1
    assert result["coverage_pct"] > 0


def test_friction_analyzer():
    trace = _make_trace()
    result = FrictionAnalyzer().analyze(trace)
    assert result["backtracks"] >= 1
    assert "insights" in result


def test_coverage_analyzer_browser():
    trace = _make_trace()
    result = CoverageAnalyzer().analyze(trace)
    assert result["coverage_type"] == "browser"
    assert "sections_total" in result


def test_coverage_analyzer_cli():
    trace = RunTrace(surface_type=SurfaceType.CLI, target="uv", task="test")
    trace.affordances = [
        Affordance(name="init", kind="command", status=AffordanceStatus.INTERACTED, relevant=True),
        Affordance(name="--help", kind="flag", status=AffordanceStatus.DISCOVERED, relevant=True),
    ]
    trace.add_step(StepRecord(step_number=1, action="init", action_type="execute", success=True))
    result = CoverageAnalyzer().analyze(trace)
    assert result["coverage_type"] == "cli"
    assert result["commands_discovered"] >= 1


def test_pipeline():
    trace = _make_trace()
    result = AnalyzerPipeline().analyze(trace)
    assert "affordance" in result
    assert "friction" in result
    assert "coverage" in result
    assert "all_insights" in result
