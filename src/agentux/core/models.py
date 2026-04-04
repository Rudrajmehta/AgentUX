"""Core domain models for AgentUX."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SurfaceType(str, Enum):
    BROWSER = "browser"
    MARKDOWN = "markdown"
    CLI = "cli"
    MCP = "mcp"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AffordanceStatus(str, Enum):
    DISCOVERED = "discovered"
    INTERACTED = "interacted"
    MISSED = "missed"
    IGNORED = "ignored"
    AMBIGUOUS = "ambiguous"


class Affordance(BaseModel):
    """A discoverable element on a surface: section, command, tool, etc."""

    name: str
    kind: str = "generic"  # section, command, subcommand, flag, tool, link, form, cta
    status: AffordanceStatus = AffordanceStatus.MISSED
    relevant: bool = True
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepRecord(BaseModel):
    """A single step in an agent's interaction trace."""

    step_number: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    thought_summary: str = ""
    action: str = ""
    action_type: str = ""  # click, type, navigate, execute, tool_call, read, search
    result: str = ""
    success: bool = True
    extracted_facts: list[str] = Field(default_factory=list)
    affordances_discovered: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScoreResult(BaseModel):
    """A single decomposable metric score."""

    name: str
    value: float = 0.0  # 0-100 scale
    weight: float = 1.0
    explanation: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    sub_scores: dict[str, float] = Field(default_factory=dict)


class ScoreCard(BaseModel):
    """Complete scoring breakdown for a run."""

    discoverability: ScoreResult = Field(default_factory=lambda: ScoreResult(name="Discoverability"))
    actionability: ScoreResult = Field(default_factory=lambda: ScoreResult(name="Actionability"))
    recovery: ScoreResult = Field(default_factory=lambda: ScoreResult(name="Recovery"))
    efficiency: ScoreResult = Field(default_factory=lambda: ScoreResult(name="Efficiency"))
    documentation_clarity: ScoreResult = Field(
        default_factory=lambda: ScoreResult(name="Documentation Clarity")
    )
    tool_clarity: ScoreResult | None = None  # CLI and MCP only
    aes: ScoreResult = Field(
        default_factory=lambda: ScoreResult(name="Agent Efficacy Score (AES)")
    )

    def as_dict(self) -> dict[str, ScoreResult]:
        result: dict[str, ScoreResult] = {
            "discoverability": self.discoverability,
            "actionability": self.actionability,
            "recovery": self.recovery,
            "efficiency": self.efficiency,
            "documentation_clarity": self.documentation_clarity,
        }
        if self.tool_clarity is not None:
            result["tool_clarity"] = self.tool_clarity
        result["aes"] = self.aes
        return result


class RunTrace(BaseModel):
    """Complete trace of a benchmark run."""

    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    surface_type: SurfaceType
    target: str
    task: str
    model: str = ""
    backend: str = ""
    status: RunStatus = RunStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    steps: list[StepRecord] = Field(default_factory=list)
    affordances: list[Affordance] = Field(default_factory=list)
    scores: ScoreCard = Field(default_factory=ScoreCard)
    total_tokens: int = 0
    total_latency_ms: float = 0.0
    success: bool = False
    failure_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    def add_step(self, step: StepRecord) -> None:
        self.steps.append(step)
        self.total_tokens += step.tokens_used
        self.total_latency_ms += step.latency_ms

    def complete(self, success: bool, failure_reason: str | None = None) -> None:
        self.status = RunStatus.COMPLETED if success else RunStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.success = success
        self.failure_reason = failure_reason

    @property
    def duration_ms(self) -> float:
        if self.completed_at is None:
            return 0.0
        return (self.completed_at - self.started_at).total_seconds() * 1000

    @property
    def step_count(self) -> int:
        return len(self.steps)


class ComparisonResult(BaseModel):
    """Result of comparing two runs."""

    run_a: RunTrace
    run_b: RunTrace
    task: str
    score_deltas: dict[str, float] = Field(default_factory=dict)
    insights: list[str] = Field(default_factory=list)
    winner: str | None = None  # "a", "b", or None for tie
    metadata: dict[str, Any] = Field(default_factory=dict)


class MonitorConfig(BaseModel):
    """Configuration for a recurring monitor."""

    name: str
    surface: SurfaceType
    target: str
    task: str
    schedule: str = "0 */6 * * *"
    backend: str = "openai"
    model: str = "gpt-4.1"
    enabled: bool = True
    thresholds: dict[str, float] = Field(default_factory=lambda: {
        "aes_drop_pct": 10.0,
        "success_rate_min": 0.8,
        "max_steps": 20,
    })
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Alert(BaseModel):
    """An alert generated by the monitoring system."""

    alert_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    monitor_name: str
    severity: str = "warning"  # info, warning, critical
    message: str
    run_id: str = ""
    baseline_run_id: str = ""
    metric: str = ""
    current_value: float = 0.0
    threshold_value: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
