"""agentux config — view and update configuration."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from agentux.core.config import load_config
from agentux.utils.console import console

app = typer.Typer(help="View and update AgentUX configuration.")


def _config_path() -> Path:
    """Find or create the global config file path."""
    # Check project-local first, then global
    local = Path.cwd() / ".agentux.yaml"
    if local.exists():
        return local
    global_dir = Path.home() / ".config" / "agentux"
    global_dir.mkdir(parents=True, exist_ok=True)
    return global_dir / "config.yaml"


def _load_raw() -> tuple[Path, dict]:
    """Load raw config dict from the active config file."""
    path = _config_path()
    raw = (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}
    return path, raw


def _save_raw(path: Path, raw: dict) -> None:
    """Save config dict back to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(raw, default_flow_style=False, sort_keys=False))


@app.callback(invoke_without_command=True)
def config_show(ctx: typer.Context) -> None:
    """Show current configuration."""
    if ctx.invoked_subcommand is not None:
        return

    path, raw = _load_raw()
    config = load_config()

    console.print(f"[bold cyan]Configuration[/]  [dim]{path}[/]\n")

    # Show the important settings
    from rich.table import Table

    table = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
    table.add_column("Setting", style="bold", width=22)
    table.add_column("Value")
    table.add_column("Source", style="dim")

    backend = raw.get("backend", {})
    table.add_row("Backend", config.backend.name, "config" if "backend" in raw else "default")
    table.add_row("Model", config.backend.model, "config" if backend.get("model") else "default")
    table.add_row(
        "Base URL",
        config.backend.base_url or "[dim]not set[/]",
        "config" if backend.get("base_url") else "—",
    )
    table.add_row(
        "API Key",
        "[green]set[/]" if config.backend.api_key else "[dim]not set (uses env)[/]",
        "config" if backend.get("api_key") else "env",
    )
    table.add_row("Max Steps", str(config.max_steps), "config" if "max_steps" in raw else "default")
    table.add_row(
        "Browser Headless",
        str(config.browser.headless),
        "config" if raw.get("browser", {}).get("headless") is not None else "default",
    )

    console.print(table)
    console.print("\n[dim]Edit: agentux config set <key> <value>[/]")
    console.print(f"[dim]File: {path}[/]")


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g. backend.model, backend.base_url)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value.

    Examples:
        agentux config set backend.model llama-3.3-70b-versatile
        agentux config set backend.base_url https://api.groq.com/openai/v1
        agentux config set backend.api_key gsk_your_key_here
        agentux config set max_steps 15
        agentux config set backend.name anthropic
    """
    path, raw = _load_raw()

    # Handle dotted keys like "backend.model"
    parts = key.split(".")
    target = raw
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            target[part] = {}
        target = target[part]

    # Type coercion for known numeric/bool fields
    final_key = parts[-1]
    if final_key in ("max_steps", "timeout_ms", "timeout_seconds", "max_tokens"):
        target[final_key] = int(value)
    elif final_key in ("headless", "allow_network", "enabled", "verbose"):
        target[final_key] = value.lower() in ("true", "1", "yes")
    elif final_key in ("temperature",):
        target[final_key] = float(value)
    else:
        target[final_key] = value

    _save_raw(path, raw)
    console.print(f"[success]{key}[/] = {value}")
    console.print(f"[dim]Saved to {path}[/]")


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Config key to read"),
) -> None:
    """Get a specific configuration value."""
    path, raw = _load_raw()

    parts = key.split(".")
    target = raw
    for part in parts:
        if isinstance(target, dict) and part in target:
            target = target[part]
        else:
            console.print(f"[dim]{key}: not set (using default)[/]")
            return

    if isinstance(target, dict):
        console.print(yaml.dump(target, default_flow_style=False))
    else:
        console.print(f"{key} = {target}")


@app.command("path")
def config_path_cmd() -> None:
    """Show the active config file path."""
    path = _config_path()
    exists = "[green]exists[/]" if path.exists() else "[dim]not created yet[/]"
    console.print(f"{path}  ({exists})")


@app.command("edit")
def config_edit() -> None:
    """Open the config file in your default editor."""
    import os
    import subprocess

    path = _config_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# AgentUX configuration\n# Run: agentux config set <key> <value>\n\n")

    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
    subprocess.run([editor, str(path)])
