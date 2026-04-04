"""Replay player for step-by-step run playback."""

from __future__ import annotations

from typing import Any

from agentux.core.models import RunTrace, StepRecord


class ReplayPlayer:
    """Steps through a recorded run trace for playback."""

    def __init__(self, trace: RunTrace) -> None:
        self.trace = trace
        self._position = 0

    @property
    def total_steps(self) -> int:
        return len(self.trace.steps)

    @property
    def current_step(self) -> int:
        return self._position

    @property
    def is_at_end(self) -> bool:
        return self._position >= self.total_steps

    def reset(self) -> None:
        self._position = 0

    def next(self) -> StepRecord | None:
        if self._position >= self.total_steps:
            return None
        step = self.trace.steps[self._position]
        self._position += 1
        return step

    def previous(self) -> StepRecord | None:
        if self._position <= 1:
            return None
        self._position -= 2
        return self.next()  # advances position by 1 and returns the step

    def goto(self, step_number: int) -> StepRecord | None:
        idx = step_number - 1
        if 0 <= idx < self.total_steps:
            self._position = idx
            return self.trace.steps[idx]
        return None

    def get_state_at_step(self, step_number: int) -> dict[str, Any]:
        """Get cumulative state up to a given step."""
        steps_so_far = self.trace.steps[:step_number]
        all_facts: list[str] = []
        all_affordances: list[str] = []
        total_tokens = 0
        total_latency = 0.0

        for step in steps_so_far:
            all_facts.extend(step.extracted_facts)
            all_affordances.extend(step.affordances_discovered)
            total_tokens += step.tokens_used
            total_latency += step.latency_ms

        return {
            "step": step_number,
            "total_steps": self.total_steps,
            "facts_so_far": all_facts,
            "affordances_so_far": list(set(all_affordances)),
            "tokens_so_far": total_tokens,
            "latency_so_far": total_latency,
            "errors_so_far": sum(1 for s in steps_so_far if s.errors),
            "success_so_far": sum(1 for s in steps_so_far if s.success),
        }
