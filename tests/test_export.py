"""Tests for export functionality."""

import json

from agentux.core.models import RunTrace, StepRecord, SurfaceType
from agentux.export.csv_export import export_csv
from agentux.export.json_export import export_json
from agentux.export.markdown_export import export_markdown
from agentux.scoring.engine import ScoringEngine


def _make_trace():
    trace = RunTrace(
        surface_type=SurfaceType.BROWSER,
        target="https://example.com",
        task="find pricing",
        model="gpt-4.1",
        backend="openai",
    )
    trace.add_step(
        StepRecord(
            step_number=1,
            thought_summary="test",
            action="click",
            action_type="click",
            success=True,
            tokens_used=100,
            extracted_facts=["found nav"],
        )
    )
    trace.add_step(
        StepRecord(
            step_number=2,
            thought_summary="done",
            action="done",
            action_type="done",
            success=True,
            tokens_used=50,
        )
    )
    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def test_json_export():
    trace = _make_trace()
    result = export_json(trace, {"insights": ["test"]})
    data = json.loads(result)
    assert data["run_id"] == trace.run_id
    assert data["analysis"]["insights"] == ["test"]


def test_markdown_export():
    trace = _make_trace()
    result = export_markdown(trace)
    assert "# AgentUX Run Report" in result
    assert trace.run_id in result
    assert "Scores" in result
    assert "Steps" in result


def test_csv_export():
    trace = _make_trace()
    result = export_csv(trace)
    lines = result.strip().split("\n")
    assert len(lines) == 3  # header + 2 steps
    assert "step" in lines[0]
    assert "click" in lines[1]
