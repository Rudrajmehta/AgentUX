"""Database access layer for AgentUX."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session, sessionmaker

from agentux.core.models import Alert, MonitorConfig, RunTrace
from agentux.storage.models import AlertRecord, Base, MonitorRecord, RunRecord


class Database:
    """SQLite-backed storage for runs, monitors, and alerts."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def _session(self) -> Session:
        return self.SessionLocal()

    # ── Runs ──

    def save_run(self, trace: RunTrace, analysis: dict[str, Any] | None = None,
                 monitor_name: str | None = None) -> None:
        with self._session() as session:
            record = RunRecord(
                run_id=trace.run_id,
                surface_type=trace.surface_type.value,
                target=trace.target,
                task=trace.task,
                model=trace.model,
                backend=trace.backend,
                status=trace.status.value,
                success=trace.success,
                failure_reason=trace.failure_reason,
                started_at=trace.started_at,
                completed_at=trace.completed_at,
                step_count=trace.step_count,
                total_tokens=trace.total_tokens,
                total_latency_ms=trace.total_latency_ms,
                aes_score=trace.scores.aes.value if trace.scores else None,
                trace_json=trace.model_dump_json(),
                analysis_json=json.dumps(analysis) if analysis else None,
                tags=",".join(trace.tags),
                monitor_name=monitor_name,
            )
            session.add(record)
            session.commit()

    def get_run(self, run_id: str) -> RunTrace | None:
        with self._session() as session:
            record = session.query(RunRecord).filter_by(run_id=run_id).first()
            if record:
                return RunTrace.model_validate_json(record.trace_json)
            return None

    def get_run_analysis(self, run_id: str) -> dict[str, Any] | None:
        with self._session() as session:
            record = session.query(RunRecord).filter_by(run_id=run_id).first()
            if record and record.analysis_json:
                return json.loads(record.analysis_json)
            return None

    def list_runs(
        self,
        limit: int = 50,
        surface_type: str | None = None,
        target: str | None = None,
        monitor_name: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._session() as session:
            query = session.query(RunRecord).order_by(desc(RunRecord.started_at))
            if surface_type:
                query = query.filter_by(surface_type=surface_type)
            if target:
                query = query.filter(RunRecord.target.contains(target))
            if monitor_name:
                query = query.filter_by(monitor_name=monitor_name)
            records = query.limit(limit).all()
            return [
                {
                    "run_id": r.run_id,
                    "surface_type": r.surface_type,
                    "target": r.target,
                    "task": r.task[:60],
                    "model": r.model,
                    "status": r.status,
                    "success": r.success,
                    "aes_score": r.aes_score,
                    "step_count": r.step_count,
                    "total_tokens": r.total_tokens,
                    "started_at": r.started_at.isoformat() if r.started_at else "",
                    "monitor_name": r.monitor_name,
                }
                for r in records
            ]

    def get_trend_data(
        self, target: str | None = None, monitor_name: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        with self._session() as session:
            query = session.query(RunRecord).order_by(RunRecord.started_at)
            if target:
                query = query.filter(RunRecord.target.contains(target))
            if monitor_name:
                query = query.filter_by(monitor_name=monitor_name)
            records = query.limit(limit).all()
            return [
                {
                    "run_id": r.run_id,
                    "started_at": r.started_at.isoformat() if r.started_at else "",
                    "aes_score": r.aes_score,
                    "success": r.success,
                    "step_count": r.step_count,
                    "total_tokens": r.total_tokens,
                    "total_latency_ms": r.total_latency_ms,
                }
                for r in records
            ]

    # ── Monitors ──

    def save_monitor(self, config: MonitorConfig) -> None:
        with self._session() as session:
            existing = session.query(MonitorRecord).filter_by(name=config.name).first()
            if existing:
                existing.surface_type = config.surface.value
                existing.target = config.target
                existing.task = config.task
                existing.schedule = config.schedule
                existing.backend = config.backend
                existing.model = config.model
                existing.enabled = config.enabled
                existing.config_json = config.model_dump_json()
            else:
                record = MonitorRecord(
                    name=config.name,
                    surface_type=config.surface.value,
                    target=config.target,
                    task=config.task,
                    schedule=config.schedule,
                    backend=config.backend,
                    model=config.model,
                    enabled=config.enabled,
                    config_json=config.model_dump_json(),
                )
                session.add(record)
            session.commit()

    def list_monitors(self) -> list[dict[str, Any]]:
        with self._session() as session:
            records = session.query(MonitorRecord).all()
            return [
                {
                    "name": r.name,
                    "surface_type": r.surface_type,
                    "target": r.target,
                    "task": r.task[:60],
                    "schedule": r.schedule,
                    "enabled": r.enabled,
                    "last_run_at": r.last_run_at.isoformat() if r.last_run_at else "never",
                }
                for r in records
            ]

    def get_monitor(self, name: str) -> MonitorConfig | None:
        with self._session() as session:
            record = session.query(MonitorRecord).filter_by(name=name).first()
            if record:
                return MonitorConfig.model_validate_json(record.config_json)
            return None

    def update_monitor_last_run(self, name: str, run_id: str) -> None:
        with self._session() as session:
            record = session.query(MonitorRecord).filter_by(name=name).first()
            if record:
                record.last_run_at = datetime.now(timezone.utc)
                record.baseline_run_id = run_id
                session.commit()

    def set_monitor_enabled(self, name: str, enabled: bool) -> None:
        with self._session() as session:
            record = session.query(MonitorRecord).filter_by(name=name).first()
            if record:
                record.enabled = enabled
                session.commit()

    # ── Alerts ──

    def save_alert(self, alert: Alert) -> None:
        with self._session() as session:
            record = AlertRecord(
                alert_id=alert.alert_id,
                monitor_name=alert.monitor_name,
                severity=alert.severity,
                message=alert.message,
                run_id=alert.run_id,
                baseline_run_id=alert.baseline_run_id,
                metric=alert.metric,
                current_value=alert.current_value,
                threshold_value=alert.threshold_value,
                created_at=alert.created_at,
                acknowledged=alert.acknowledged,
            )
            session.add(record)
            session.commit()

    def list_alerts(self, limit: int = 50, unacknowledged_only: bool = False) -> list[dict[str, Any]]:
        with self._session() as session:
            query = session.query(AlertRecord).order_by(desc(AlertRecord.created_at))
            if unacknowledged_only:
                query = query.filter_by(acknowledged=False)
            records = query.limit(limit).all()
            return [
                {
                    "alert_id": r.alert_id,
                    "monitor_name": r.monitor_name,
                    "severity": r.severity,
                    "message": r.message,
                    "metric": r.metric,
                    "current_value": r.current_value,
                    "threshold_value": r.threshold_value,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                    "acknowledged": r.acknowledged,
                }
                for r in records
            ]

    def acknowledge_alert(self, alert_id: str) -> None:
        with self._session() as session:
            record = session.query(AlertRecord).filter_by(alert_id=alert_id).first()
            if record:
                record.acknowledged = True
                session.commit()
