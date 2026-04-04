"""Tests for storage layer."""

import tempfile
from pathlib import Path

import pytest

from agentux.core.models import Alert, MonitorConfig, RunTrace, SurfaceType
from agentux.storage.database import Database


@pytest.fixture
def db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield Database(f"sqlite:///{db_path}")


@pytest.fixture
def sample_trace():
    from tests.conftest import make_sample_trace
    return make_sample_trace()


def make_sample_trace():
    from agentux.core.models import StepRecord, Affordance, AffordanceStatus, ScoreCard, ScoreResult
    trace = RunTrace(
        surface_type=SurfaceType.BROWSER,
        target="https://example.com",
        task="find pricing",
        model="gpt-4.1",
        backend="openai",
    )
    trace.add_step(StepRecord(
        step_number=1, thought_summary="test", action="click",
        action_type="click", success=True, tokens_used=100, latency_ms=500,
    ))
    trace.complete(success=True)

    from agentux.scoring.engine import ScoringEngine
    trace.scores = ScoringEngine().score(trace)
    return trace


def test_save_and_get_run(db):
    trace = make_sample_trace()
    db.save_run(trace, {"test": True})
    retrieved = db.get_run(trace.run_id)
    assert retrieved is not None
    assert retrieved.run_id == trace.run_id
    assert retrieved.target == "https://example.com"


def test_list_runs(db):
    trace = make_sample_trace()
    db.save_run(trace)
    runs = db.list_runs(limit=10)
    assert len(runs) >= 1
    assert runs[0]["run_id"] == trace.run_id


def test_get_run_analysis(db):
    trace = make_sample_trace()
    db.save_run(trace, {"insights": ["test insight"]})
    analysis = db.get_run_analysis(trace.run_id)
    assert analysis is not None
    assert "insights" in analysis


def test_monitors_crud(db):
    monitor = MonitorConfig(
        name="test-monitor",
        surface=SurfaceType.BROWSER,
        target="https://example.com",
        task="find pricing",
    )
    db.save_monitor(monitor)
    monitors = db.list_monitors()
    assert len(monitors) == 1
    assert monitors[0]["name"] == "test-monitor"

    retrieved = db.get_monitor("test-monitor")
    assert retrieved is not None
    assert retrieved.target == "https://example.com"


def test_monitor_enable_disable(db):
    monitor = MonitorConfig(
        name="test-monitor",
        surface=SurfaceType.BROWSER,
        target="https://example.com",
        task="test",
    )
    db.save_monitor(monitor)
    db.set_monitor_enabled("test-monitor", False)
    monitors = db.list_monitors()
    assert not monitors[0]["enabled"]


def test_alerts(db):
    alert = Alert(
        monitor_name="test-monitor",
        severity="warning",
        message="AES dropped 15%",
        metric="aes",
        current_value=60.0,
        threshold_value=10.0,
    )
    db.save_alert(alert)
    alerts = db.list_alerts()
    assert len(alerts) == 1
    assert alerts[0]["message"] == "AES dropped 15%"

    db.acknowledge_alert(alert.alert_id)
    unacked = db.list_alerts(unacknowledged_only=True)
    assert len(unacked) == 0


def test_trend_data(db):
    for _ in range(3):
        trace = make_sample_trace()
        db.save_run(trace)
    data = db.get_trend_data(limit=10)
    assert len(data) == 3
