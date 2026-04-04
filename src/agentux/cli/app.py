"""Main CLI application — entry point for all agentux commands."""

from __future__ import annotations

import typer

from agentux.cli.commands.alerts import app as alerts_app
from agentux.cli.commands.config_cmd import app as config_app
from agentux.cli.commands.monitor import app as monitor_app

app = typer.Typer(
    name="agentux",
    help="AgentUX — Synthetic observability for agent usability.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    add_completion=False,
    invoke_without_command=True,
)


@app.callback(invoke_without_command=True)
def _root_callback(ctx: typer.Context) -> None:
    """Show banner + quickstart when invoked with no args."""
    if ctx.invoked_subcommand is None:
        from agentux.utils.branding import print_banner
        from agentux.utils.console import console

        print_banner()
        console.print("[bold]Quick start:[/]")
        console.print("  agentux init                           [dim]# setup wizard[/]")
        console.print("  agentux doctor                         [dim]# verify deps[/]")
        console.print("  agentux run URL --task '...'            [dim]# run benchmark[/]")
        console.print("  agentux --help                         [dim]# all commands[/]")
        console.print()


# ═══════════════════════════════════════════════════════════════════════════
# SETUP — run these first
# ═══════════════════════════════════════════════════════════════════════════


@app.command("init", rich_help_panel="Setup")
def init_command(
    directory: str = typer.Argument(".", help="Directory to initialize in"),
) -> None:
    """Interactive setup wizard — choose provider, model, API key."""
    from agentux.cli.commands.init_cmd import init as _init

    _init(directory=directory)


@app.command("doctor", rich_help_panel="Setup")
def doctor_command() -> None:
    """Check dependencies, credentials, and system readiness."""
    from agentux.cli.commands.doctor import doctor as _doctor

    _doctor()


app.add_typer(
    config_app, name="config", help="View and update configuration", rich_help_panel="Setup"
)


# ═══════════════════════════════════════════════════════════════════════════
# EVALUATE — run benchmarks
# ═══════════════════════════════════════════════════════════════════════════


@app.command("run", rich_help_panel="Evaluate")
def run_command(
    target: str = typer.Argument(..., help="Target URL, file path, or command"),
    task: str = typer.Option("", "--task", "-t", help="Task description (omit for general audit)"),
    surface: str = typer.Option(
        "browser", "--surface", "-s", help="Surface type: browser, markdown, cli, mcp"
    ),
    backend: str = typer.Option(
        "", "--backend", "-b", help="Backend override (uses config default)"
    ),
    model: str = typer.Option("", "--model", "-m", help="Model override (uses config default)"),
    base_url: str = typer.Option(
        "", "--base-url", help="API base URL override (uses config default)"
    ),
    max_steps: int = typer.Option(0, "--max-steps", help="Max steps (0 = use config default)"),
    headless: bool = typer.Option(True, "--headless/--visible", help="Browser headless mode"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend (no API key needed)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    tag: list[str] | None = typer.Option(None, "--tag", help="Tags for this run"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file path"),
) -> None:
    """Run a benchmark evaluation against a target."""
    from agentux.cli.commands.run import run_command as _run

    _run(
        target=target,
        task=task,
        surface=surface,
        backend=backend,
        model=model,
        base_url=base_url,
        max_steps=max_steps,
        headless=headless,
        demo=demo,
        verbose=verbose,
        tag=tag,
        config_path=config_path,
    )


@app.command("compare", rich_help_panel="Evaluate")
def compare_command(
    target_a: str = typer.Argument(..., help="First target (URL, path, or command)"),
    task: str = typer.Option("", "--task", "-t", help="Task for both (omit for general audit)"),
    target_b: str = typer.Option("", "--markdown", "--vs", "-B", help="Second target to compare"),
    surface_a: str = typer.Option("browser", "--surface-a", "-sa", help="Surface A type"),
    surface_b: str = typer.Option("markdown", "--surface-b", "-sb", help="Surface B type"),
    backend: str = typer.Option("", "--backend", "-b", help="Backend override"),
    model: str = typer.Option("", "--model", "-m", help="Model override"),
    max_steps: int = typer.Option(0, "--max-steps", help="Max steps per run"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend"),
    config_path: str | None = typer.Option(None, "--config", "-c", help="Config file"),
) -> None:
    """Compare agent usability between two targets."""
    from agentux.cli.commands.compare import compare_command as _compare

    _compare(
        target_a=target_a,
        task=task,
        target_b=target_b,
        surface_a=surface_a,
        surface_b=surface_b,
        backend=backend,
        model=model,
        max_steps=max_steps,
        demo=demo,
        config_path=config_path,
    )


@app.command("cli", rich_help_panel="Evaluate")
def cli_shortcut(
    tool: str = typer.Argument(..., help="CLI tool name"),
    task: str = typer.Option("", "--task", "-t", help="Task (omit for general audit)"),
    backend: str = typer.Option("", "--backend", "-b", help="Backend override"),
    demo: bool = typer.Option(False, "--demo"),
    max_steps: int = typer.Option(0, "--max-steps"),
) -> None:
    """Evaluate a CLI tool's agent usability."""
    from agentux.cli.commands.run import run_command as _run

    _run(
        target=tool,
        task=task,
        surface="cli",
        backend=backend,
        model="",
        base_url="",
        max_steps=max_steps,
        headless=True,
        demo=demo,
        verbose=False,
        tag=None,
        config_path=None,
    )


@app.command("mcp", rich_help_panel="Evaluate")
def mcp_shortcut(
    task: str = typer.Option("", "--task", "-t", help="Task (omit for general audit)"),
    command: str = typer.Option("", "--command", "-c", help="MCP server command"),
    backend: str = typer.Option("", "--backend", "-b", help="Backend override"),
    demo: bool = typer.Option(False, "--demo"),
    max_steps: int = typer.Option(0, "--max-steps"),
) -> None:
    """Evaluate an MCP server's tool discoverability."""
    from agentux.cli.commands.run import run_command as _run

    _run(
        target=command,
        task=task,
        surface="mcp",
        backend=backend,
        model="",
        base_url="",
        max_steps=max_steps,
        headless=True,
        demo=demo,
        verbose=False,
        tag=None,
        config_path=None,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE — inspect results
# ═══════════════════════════════════════════════════════════════════════════


@app.command("runs", rich_help_panel="Analyze")
def runs_command(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show"),
    surface: str | None = typer.Option(None, "--surface", "-s", help="Filter by surface type"),
    target: str | None = typer.Option(None, "--target", help="Filter by target (substring)"),
) -> None:
    """List all past runs."""
    from agentux.cli.formatters import print_runs_table
    from agentux.core.config import load_config
    from agentux.storage.database import Database

    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)
    run_list = db.list_runs(limit=limit, surface_type=surface, target=target)
    if not run_list:
        from agentux.utils.console import console

        console.print("[dim]No runs yet. Try: agentux run URL --task '...'[/]")
        return
    print_runs_table(run_list)


@app.command("inspect", rich_help_panel="Analyze")
def inspect_command(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    analysis: bool = typer.Option(False, "--analysis", "-a", help="Show full analysis"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Inspect a specific run in detail."""
    from agentux.cli.commands.inspect_cmd import inspect_run as _inspect

    _inspect(run_id=run_id, analysis=analysis, json_output=json_output)


@app.command("replay", rich_help_panel="Analyze")
def replay_command(
    run_id: str = typer.Argument(..., help="Run ID to replay"),
    speed: float = typer.Option(1.0, "--speed", help="Replay speed multiplier"),
    step_mode: bool = typer.Option(False, "--step", help="Step through manually"),
) -> None:
    """Replay a past run step by step in the terminal."""
    from agentux.cli.commands.replay import replay as _replay

    _replay(run_id=run_id, speed=speed, step_mode=step_mode)


@app.command("trends", rich_help_panel="Analyze")
def trends_command(
    target: str | None = typer.Option(None, "--target", help="Filter by target"),
    monitor: str | None = typer.Option(None, "--monitor", help="Filter by monitor"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs"),
) -> None:
    """View AES trends and historical data."""
    from agentux.cli.commands.trends import trends as _trends

    _trends(target=target, monitor=monitor, limit=limit)


@app.command("export", rich_help_panel="Analyze")
def export_command(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="json, markdown, or csv"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export a run as JSON, Markdown, or CSV."""
    from agentux.cli.commands.export_cmd import export as _export

    _export(run_id=run_id, format=format, output=output)


# ═══════════════════════════════════════════════════════════════════════════
# MONITOR — continuous observability
# ═══════════════════════════════════════════════════════════════════════════

app.add_typer(
    monitor_app,
    name="monitor",
    help="Add, list, run, enable/disable monitors",
    rich_help_panel="Monitor",
)
app.add_typer(
    alerts_app, name="alerts", help="View and acknowledge alerts", rich_help_panel="Monitor"
)


# ═══════════════════════════════════════════════════════════════════════════
# TUI
# ═══════════════════════════════════════════════════════════════════════════


@app.command("tui", rich_help_panel="Interface")
def launch_tui() -> None:
    """Launch the interactive terminal dashboard."""
    from agentux.tui.app import AgentUXApp

    tui = AgentUXApp()
    tui.run()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
