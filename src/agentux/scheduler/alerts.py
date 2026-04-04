"""Alert generation and delivery."""

from __future__ import annotations

import logging
from typing import Any

from agentux.core.models import Alert, MonitorConfig, RunTrace
from agentux.storage.database import Database

logger = logging.getLogger(__name__)


def check_thresholds(
    trace: RunTrace,
    monitor: MonitorConfig,
    db: Database,
) -> list[Alert]:
    """Check run results against monitor thresholds and generate alerts."""
    alerts: list[Alert] = []
    thresholds = monitor.thresholds

    # AES drop check
    aes_drop_pct = thresholds.get("aes_drop_pct", 10.0)
    runs = db.get_trend_data(monitor_name=monitor.name, limit=5)
    if len(runs) >= 2:
        prev_aes = runs[-2].get("aes_score", 0) or 0
        curr_aes = trace.scores.aes.value
        if prev_aes > 0:
            drop_pct = (prev_aes - curr_aes) / prev_aes * 100
            if drop_pct > aes_drop_pct:
                alerts.append(Alert(
                    monitor_name=monitor.name,
                    severity="warning",
                    message=f"AES dropped {drop_pct:.0f}% ({prev_aes:.0f} -> {curr_aes:.0f})",
                    run_id=trace.run_id,
                    metric="aes",
                    current_value=curr_aes,
                    threshold_value=aes_drop_pct,
                ))

    # Success rate check
    success_min = thresholds.get("success_rate_min", 0.8)
    if not trace.success:
        # Check recent success rate
        recent = db.get_trend_data(monitor_name=monitor.name, limit=10)
        if recent:
            success_rate = sum(1 for r in recent if r["success"]) / len(recent)
            if success_rate < success_min:
                alerts.append(Alert(
                    monitor_name=monitor.name,
                    severity="critical" if success_rate < 0.5 else "warning",
                    message=f"Success rate {success_rate:.0%} below threshold {success_min:.0%}",
                    run_id=trace.run_id,
                    metric="success_rate",
                    current_value=success_rate,
                    threshold_value=success_min,
                ))

    # Max steps check
    max_steps = thresholds.get("max_steps", 20)
    if trace.step_count > max_steps:
        alerts.append(Alert(
            monitor_name=monitor.name,
            severity="info",
            message=f"Run took {trace.step_count} steps (threshold: {max_steps})",
            run_id=trace.run_id,
            metric="step_count",
            current_value=float(trace.step_count),
            threshold_value=float(max_steps),
        ))

    # Hard failure
    if not trace.success and trace.failure_reason:
        alerts.append(Alert(
            monitor_name=monitor.name,
            severity="critical",
            message=f"Task failed: {trace.failure_reason[:100]}",
            run_id=trace.run_id,
            metric="task_success",
            current_value=0.0,
            threshold_value=1.0,
        ))

    return alerts


def deliver_alert(alert: Alert, config: dict[str, Any]) -> None:
    """Deliver an alert via configured channels (Slack, Discord, etc.).

    Extension point for alert delivery integrations.
    """
    # Slack webhook
    slack_url = config.get("slack_webhook", "")
    if slack_url:
        try:
            import httpx

            payload = {
                "text": f":warning: AgentUX Alert [{alert.severity}]\n"
                        f"Monitor: {alert.monitor_name}\n"
                        f"{alert.message}",
            }
            httpx.post(slack_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Slack alert delivery failed: {e}")

    # Discord webhook
    discord_url = config.get("discord_webhook", "")
    if discord_url:
        try:
            import httpx

            payload = {
                "content": f"**AgentUX Alert** [{alert.severity}]\n"
                           f"Monitor: {alert.monitor_name}\n"
                           f"{alert.message}",
            }
            httpx.post(discord_url, json=payload, timeout=10)
        except Exception as e:
            logger.error(f"Discord alert delivery failed: {e}")
