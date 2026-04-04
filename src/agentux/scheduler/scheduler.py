"""Built-in scheduler for recurring monitor execution."""

from __future__ import annotations

import asyncio
import logging

from agentux.core.config import AgentUXConfig
from agentux.core.runner import Runner, create_backend, create_surface
from agentux.scheduler.alerts import check_thresholds
from agentux.storage.database import Database

logger = logging.getLogger(__name__)


class MonitorScheduler:
    """Runs configured monitors on their cron schedules.

    Uses APScheduler for cron-based scheduling. Each monitor
    triggers a full benchmark run and checks thresholds for alerts.
    """

    def __init__(self, config: AgentUXConfig, db: Database) -> None:
        self.config = config
        self.db = db
        self._scheduler = None

    def start(self) -> None:
        """Start the scheduler with all enabled monitors."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.error("APScheduler not installed. Run: pip install apscheduler")
            return

        self._scheduler = BackgroundScheduler()

        monitors = self.db.list_monitors()
        for monitor_data in monitors:
            if not monitor_data["enabled"]:
                continue

            name = monitor_data["name"]
            schedule = monitor_data["schedule"]

            try:
                parts = schedule.split()
                if len(parts) == 5:
                    trigger = CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4],
                    )
                    self._scheduler.add_job(  # type: ignore[attr-defined]
                        self._run_monitor,
                        trigger,
                        args=[name],
                        id=f"monitor_{name}",
                        replace_existing=True,
                    )
                    logger.info(f"Scheduled monitor '{name}' with schedule: {schedule}")
            except Exception as e:
                logger.error(f"Failed to schedule monitor '{name}': {e}")

        self._scheduler.start()  # type: ignore[attr-defined]
        logger.info("Scheduler started")

    def stop(self) -> None:
        if self._scheduler:
            self._scheduler.shutdown()

    def _run_monitor(self, name: str) -> None:
        """Execute a single monitor run (called by scheduler)."""
        monitor = self.db.get_monitor(name)
        if not monitor:
            logger.error(f"Monitor '{name}' not found")
            return

        logger.info(f"Running monitor: {name}")

        try:
            runner = Runner(self.config)
            surface = create_surface(monitor.surface, monitor.target, self.config)
            backend = create_backend(monitor.backend, self.config)

            trace, analysis = asyncio.run(
                runner.run(
                    surface,
                    backend,
                    monitor.task,
                    monitor.target,
                    tags=["monitor", name],
                )
            )

            self.db.save_run(trace, analysis, monitor_name=name)
            self.db.update_monitor_last_run(name, trace.run_id)

            # Check thresholds
            alerts = check_thresholds(trace, monitor, self.db)
            for alert in alerts:
                self.db.save_alert(alert)
                logger.warning(f"Alert: {alert.message}")

            logger.info(f"Monitor '{name}' completed. AES: {trace.scores.aes.value:.0f}")

        except Exception as e:
            logger.error(f"Monitor '{name}' failed: {e}")
