"""SQLAlchemy models for persistent storage."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(24), unique=True, nullable=False, index=True)
    surface_type = Column(String(20), nullable=False, index=True)
    target = Column(String(2048), nullable=False)
    task = Column(Text, nullable=False)
    model = Column(String(100), default="")
    backend = Column(String(50), default="")
    status = Column(String(20), default="pending")
    success = Column(Boolean, default=False)
    failure_reason = Column(Text, nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime, nullable=True)
    step_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_latency_ms = Column(Float, default=0.0)
    aes_score = Column(Float, nullable=True)
    trace_json = Column(Text, nullable=False, default="{}")
    analysis_json = Column(Text, nullable=True)
    tags = Column(String(500), default="")
    monitor_name = Column(String(200), nullable=True, index=True)


class MonitorRecord(Base):
    __tablename__ = "monitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    surface_type = Column(String(20), nullable=False)
    target = Column(String(2048), nullable=False)
    task = Column(Text, nullable=False)
    schedule = Column(String(100), default="0 */6 * * *")
    backend = Column(String(50), default="openai")
    model = Column(String(100), default="gpt-4.1")
    enabled = Column(Boolean, default=True)
    config_json = Column(Text, default="{}")
    baseline_run_id = Column(String(24), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    last_run_at = Column(DateTime, nullable=True)


class AlertRecord(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(24), unique=True, nullable=False, index=True)
    monitor_name = Column(String(200), nullable=False, index=True)
    severity = Column(String(20), default="warning")
    message = Column(Text, nullable=False)
    run_id = Column(String(24), default="")
    baseline_run_id = Column(String(24), default="")
    metric = Column(String(100), default="")
    current_value = Column(Float, default=0.0)
    threshold_value = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    acknowledged = Column(Boolean, default=False)
