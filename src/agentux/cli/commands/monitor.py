"""agentux monitor — manage recurring monitors."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from agentux.core.config import load_config
from agentux.core.models import MonitorConfig, SurfaceType
from agentux.storage.database import Database
from agentux.utils.console import console

app = typer.Typer(help="Manage recurring monitors.")


@app.command("add")
def monitor_add(
    config_file: str = typer.Argument(..., help="Path to monitor YAML config"),
) -> None:
    """Add a monitor from a YAML config file."""
    path = Path(config_file)
    if not path.exists():
        console.print(f"[error]File not found: {config_file}[/]")
        raise typer.Exit(1)

    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        console.print("[error]Invalid monitor config[/]")
        raise typer.Exit(1)

    monitor = MonitorConfig(
        name=raw["name"],
        surface=SurfaceType(raw["surface"]),
        target=raw["target"],
        task=raw["task"],
        schedule=raw.get("schedule", "0 */6 * * *"),
        backend=raw.get("backend", "openai"),
        model=raw.get("model", "gpt-4.1"),
        enabled=raw.get("enabled", True),
        thresholds=raw.get("thresholds", {}),
        tags=raw.get("tags", []),
    )

    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    db.save_monitor(monitor)
    console.print(f"[success]Monitor '{monitor.name}' added.[/]")
    console.print(f"  Schedule: {monitor.schedule}")
    console.print(f"  Target: {monitor.target}")


@app.command("list")
def monitor_list() -> None:
    """List all configured monitors."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    monitors = db.list_monitors()

    if not monitors:
        console.print("[dim]No monitors configured. Use `agentux monitor add` to create one.[/]")
        return

    from rich.table import Table

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name", width=20)
    table.add_column("Surface", width=10)
    table.add_column("Target", width=30)
    table.add_column("Schedule", width=16)
    table.add_column("Enabled", width=8)
    table.add_column("Last Run", width=20)

    for m in monitors:
        table.add_row(
            m["name"],
            m["surface_type"],
            m["target"][:28],
            m["schedule"],
            "[green]Yes[/]" if m["enabled"] else "[red]No[/]",
            m["last_run_at"],
        )

    console.print(table)


@app.command("run")
def monitor_run(
    name: str = typer.Argument(..., help="Monitor name to run"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend"),
) -> None:
    """Manually trigger a monitor run."""
    import asyncio

    from agentux.cli.formatters import print_run_summary, print_scorecard
    from agentux.core.runner import Runner, create_backend, create_surface

    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    monitor = db.get_monitor(name)
    if not monitor:
        console.print(f"[error]Monitor '{name}' not found.[/]")
        raise typer.Exit(1)

    if demo:
        config.demo_mode = True

    config.backend.model = monitor.model
    runner = Runner(config)
    surface = create_surface(monitor.surface, monitor.target, config)
    backend_name = "mock" if demo else monitor.backend
    agent_backend = create_backend(backend_name, config)

    console.print(f"[bold]Running monitor: {name}[/]")
    trace, analysis = asyncio.run(
        runner.run(surface, agent_backend, monitor.task, monitor.target, tags=["monitor", name])
    )

    print_run_summary(trace)
    print_scorecard(trace.scores)

    db.save_run(trace, analysis, monitor_name=name)
    db.update_monitor_last_run(name, trace.run_id)

    # Check thresholds
    from agentux.scheduler.alerts import check_thresholds

    alerts = check_thresholds(trace, monitor, db)
    if alerts:
        console.print(f"\n[warning]{len(alerts)} alert(s) generated![/]")
        for alert in alerts:
            db.save_alert(alert)
            console.print(f"  [yellow]![/] {alert.message}")

        # Deliver via webhooks if configured
        from agentux.scheduler.alerts import deliver_alert

        alert_cfg = {
            "slack_webhook": config.alerts.slack_webhook,
            "discord_webhook": config.alerts.discord_webhook,
        }
        for alert in alerts:
            deliver_alert(alert, alert_cfg)


@app.command("enable")
def monitor_enable(name: str = typer.Argument(..., help="Monitor name")) -> None:
    """Enable a monitor."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    db.set_monitor_enabled(name, True)
    console.print(f"[success]Monitor '{name}' enabled.[/]")


@app.command("disable")
def monitor_disable(name: str = typer.Argument(..., help="Monitor name")) -> None:
    """Disable a monitor."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    db.set_monitor_enabled(name, False)
    console.print(f"Monitor '{name}' disabled.")
