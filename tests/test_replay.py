"""Tests for replay player."""

from agentux.core.models import RunTrace, StepRecord, SurfaceType
from agentux.replay.player import ReplayPlayer
from agentux.scoring.engine import ScoringEngine


def _make_trace():
    trace = RunTrace(
        surface_type=SurfaceType.BROWSER,
        target="https://example.com",
        task="find pricing",
    )
    for i in range(5):
        trace.add_step(StepRecord(
            step_number=i + 1, action=f"action_{i}", action_type="click",
            success=True, tokens_used=100, extracted_facts=[f"fact_{i}"],
        ))
    trace.complete(success=True)
    trace.scores = ScoringEngine().score(trace)
    return trace


def test_replay_navigation():
    player = ReplayPlayer(_make_trace())
    assert player.total_steps == 5
    assert player.current_step == 0

    step = player.next()
    assert step.step_number == 1
    assert player.current_step == 1

    step = player.next()
    assert step.step_number == 2

    step = player.previous()
    assert step.step_number == 1


def test_replay_goto():
    player = ReplayPlayer(_make_trace())
    step = player.goto(3)
    assert step.step_number == 3


def test_replay_state():
    player = ReplayPlayer(_make_trace())
    state = player.get_state_at_step(3)
    assert state["step"] == 3
    assert len(state["facts_so_far"]) == 3
    assert state["tokens_so_far"] == 300


def test_replay_bounds():
    player = ReplayPlayer(_make_trace())
    # Go past end
    for _ in range(10):
        player.next()
    assert player.is_at_end
    assert player.next() is None
