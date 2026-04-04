"""Main CLI application — entry point for all agentux commands."""

from __future__ import annotations

import typer

from agentux.cli.commands.alerts import app as alerts_app
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
        console.print(
            "  agentux doctor                                      [dim]# verify setup[/]"
        )
        console.print(
            "  agentux run URL --task '...' --demo                 [dim]# demo run (no API key)[/]"
        )
        console.print(
            "  agentux run URL --task '...'                   [dim]# real run (needs key)[/]"
        )
        console.print(
            "  agentux compare URL --vs URL2 --task '...' --demo   [dim]# compare surfaces[/]"
        )
        console.print(
            "  agentux --help                                      [dim]# all commands[/]"
        )
        console.print()


# Only multi-subcommand groups use add_typer
app.add_typer(monitor_app, name="monitor", help="Manage recurring monitors")
app.add_typer(alerts_app, name="alerts", help="View and manage alerts")


# ── run ──────────────────────────────────────────────────────────────────────


@app.command("run")
def run_command(
    target: str = typer.Argument(..., help="Target URL, file path, or command to evaluate"),
    task: str = typer.Option(..., "--task", "-t", help="Task description for the agent"),
    surface: str = typer.Option(
        "browser",
        "--surface",
        "-s",
        help="Surface type: browser, markdown, cli, mcp",
    ),
    backend: str = typer.Option(
        "openai", "--backend", "-b", help="Agent backend: openai, anthropic, mock"
    ),
    model: str = typer.Option("", "--model", "-m", help="Model name override"),
    base_url: str = typer.Option(
        "", "--base-url", help="OpenAI-compatible API base URL (e.g. Groq, OpenRouter)"
    ),
    max_steps: int = typer.Option(25, "--max-steps", help="Maximum steps"),
    headless: bool = typer.Option(True, "--headless/--visible", help="Browser headless mode"),
    demo: bool = typer.Option(False, "--demo", help="Use mock backend for demo"),
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


# ── compare ──────────────────────────────────────────────────────────────────


@app.command("compare")
def compare_command(
    target_a: str = typer.Argument(..., help="First target (URL, path, or command)"),
    task: str = typer.Option(..., "--task", "-t", help="Task for both targets"),
    target_b: str = typer.Option(
        "", "--markdown", "--vs", "-B", help="Second target to compare against"
    ),
    surface_a: str = typer.Option(
        "browser", "--surface-a", "-sa", help="Surface type for target A"
    ),
    surface_b: str = typer.Option(
        "markdown", "--surface-b", "-sb", help="Surface type for target B"
    ),
    backend: str = typer.Option("openai", "--backend", "-b", help="Agent backend"),
    model: str = typer.Option("", "--model", "-m", help="Model override"),
    max_steps: int = typer.Option(25, "--max-steps", help="Max steps per run"),
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


# ── replay ───────────────────────────────────────────────────────────────────


@app.command("replay")
def replay_command(
    run_id: str = typer.Argument(..., help="Run ID to replay"),
    speed: float = typer.Option(1.0, "--speed", help="Replay speed multiplier"),
    step_mode: bool = typer.Option(False, "--step", help="Step through one at a time"),
) -> None:
    """Replay a past run step by step in the terminal."""
    from agentux.cli.commands.replay import replay as _replay

    _replay(run_id=run_id, speed=speed, step_mode=step_mode)


# ── trends ───────────────────────────────────────────────────────────────────


@app.command("trends")
def trends_command(
    target: str | None = typer.Option(None, "--target", help="Filter by target"),
    monitor: str | None = typer.Option(None, "--monitor", help="Filter by monitor name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of runs to show"),
) -> None:
    """View AES trends and historical data."""
    from agentux.cli.commands.trends import trends as _trends

    _trends(target=target, monitor=monitor, limit=limit)


# ── inspect ──────────────────────────────────────────────────────────────────


@app.command("inspect")
def inspect_command(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    analysis: bool = typer.Option(False, "--analysis", "-a", help="Show full analysis"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
) -> None:
    """Inspect a specific run in detail."""
    from agentux.cli.commands.inspect_cmd import inspect_run as _inspect

    _inspect(run_id=run_id, analysis=analysis, json_output=json_output)


# ── export ───────────────────────────────────────────────────────────────────


@app.command("export")
def export_command(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, markdown, csv"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export a run as JSON, Markdown, or CSV."""
    from agentux.cli.commands.export_cmd import export as _export

    _export(run_id=run_id, format=format, output=output)


# ── doctor ───────────────────────────────────────────────────────────────────


@app.command("doctor")
def doctor_command() -> None:
    """Run diagnostics to verify AgentUX dependencies and configuration."""
    from agentux.cli.commands.doctor import doctor as _doctor

    _doctor()


# ── init ─────────────────────────────────────────────────────────────────────


@app.command("init")
def init_command(
    directory: str = typer.Argument(".", help="Directory to initialize in"),
) -> None:
    """Initialize AgentUX configuration in the current directory."""
    from agentux.cli.commands.init_cmd import init as _init

    _init(directory=directory)


# ── tui ──────────────────────────────────────────────────────────────────────


@app.command("tui")
def launch_tui() -> None:
    """Launch the interactive TUI dashboard."""
    from agentux.tui.app import AgentUXApp

    tui = AgentUXApp()
    tui.run()


# ── cli shortcut ─────────────────────────────────────────────────────────────


@app.command("cli")
def cli_shortcut(
    tool: str = typer.Argument(..., help="CLI tool name"),
    task: str = typer.Option(..., "--task", "-t", help="Task description"),
    backend: str = typer.Option("openai", "--backend", "-b"),
    demo: bool = typer.Option(False, "--demo"),
    max_steps: int = typer.Option(25, "--max-steps"),
) -> None:
    """Evaluate a CLI tool (shortcut for run --surface cli)."""
    from agentux.cli.commands.run import run_command as _run

    _run(
        target=tool,
        task=task,
        surface="cli",
        backend=backend,
        model="",
        max_steps=max_steps,
        headless=True,
        demo=demo,
        verbose=False,
        tag=None,
        config_path=None,
    )


# ── mcp shortcut ─────────────────────────────────────────────────────────────


@app.command("mcp")
def mcp_shortcut(
    task: str = typer.Option(..., "--task", "-t", help="Task description"),
    command: str = typer.Option("", "--command", "-c", help="MCP server command"),
    backend: str = typer.Option("openai", "--backend", "-b"),
    demo: bool = typer.Option(False, "--demo"),
    max_steps: int = typer.Option(25, "--max-steps"),
) -> None:
    """Evaluate an MCP server (shortcut for run --surface mcp)."""
    from agentux.cli.commands.run import run_command as _run

    _run(
        target=command,
        task=task,
        surface="mcp",
        backend=backend,
        model="",
        max_steps=max_steps,
        headless=True,
        demo=demo,
        verbose=False,
        tag=None,
        config_path=None,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
