"""agentux init — interactive setup wizard."""

from __future__ import annotations

import os
from pathlib import Path

import typer
import yaml

from agentux.core.config import default_data_dir
from agentux.utils.branding import print_banner
from agentux.utils.console import console

app = typer.Typer()

PROVIDERS = {
    "1": ("groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "OPENAI_API_KEY"),
    "2": ("openai", "", "gpt-4o-mini", "OPENAI_API_KEY"),
    "3": ("anthropic", "", "claude-sonnet-4-20250514", "ANTHROPIC_API_KEY"),
    "4": (
        "openrouter",
        "https://openrouter.ai/api/v1",
        "meta-llama/llama-3.3-70b",
        "OPENAI_API_KEY",
    ),
    "5": ("custom", "", "", "OPENAI_API_KEY"),
}


@app.callback(invoke_without_command=True)
def init(
    directory: str = typer.Argument(".", help="Directory to initialize in"),
) -> None:
    """Interactive setup wizard for AgentUX."""
    print_banner()

    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)
    config_path = target / ".agentux.yaml"

    if config_path.exists():
        console.print(f"[warning]Config already exists: {config_path}[/]")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit()

    console.print("[bold]Let's set up AgentUX.[/]\n")

    # Step 1: Choose provider
    console.print("[bold]1. Choose your LLM provider:[/]")
    console.print("   [cyan]1[/]  Groq          [dim](free, fast, recommended)[/]")
    console.print("   [cyan]2[/]  OpenAI        [dim](requires billing)[/]")
    console.print("   [cyan]3[/]  Anthropic     [dim](requires billing)[/]")
    console.print("   [cyan]4[/]  OpenRouter    [dim](free tier available)[/]")
    console.print("   [cyan]5[/]  Custom        [dim](any OpenAI-compatible endpoint)[/]")
    console.print()

    choice = typer.prompt("  Select", default="1")
    provider_info = PROVIDERS.get(choice, PROVIDERS["1"])
    provider_name, default_base_url, default_model, env_key = provider_info

    # Step 2: Model
    model = default_model
    if choice == "5":
        model = typer.prompt("  Model name", default="")
    else:
        use_default = typer.confirm(f"  Use default model ({default_model})?", default=True)
        if not use_default:
            model = typer.prompt("  Model name")

    # Step 3: Base URL (for custom/groq/openrouter)
    base_url = default_base_url
    if choice == "5":
        base_url = typer.prompt("  API base URL", default="")

    # Step 4: API key
    console.print()
    existing_key = os.environ.get(env_key, "")
    if existing_key:
        console.print(f"[green]  {env_key} already set in environment.[/]")
        api_key = ""  # don't store, use env
    else:
        console.print(
            f"  [bold]2. API key[/] [dim](stored in config, or set {env_key} in your shell)[/]"
        )
        api_key = typer.prompt("  API key (or Enter to skip)", default="", show_default=False)

    # Step 5: Max steps
    console.print()
    max_steps = typer.prompt("  Max steps per run", default="15", show_default=True)

    # Build config
    config: dict = {
        "backend": {
            "name": "anthropic" if provider_name == "anthropic" else "openai",
            "model": model,
        },
        "max_steps": int(max_steps),
        "browser": {"headless": True, "timeout_ms": 30000},
        "cli": {"timeout_seconds": 30, "allow_network": False},
    }

    if base_url:
        config["backend"]["base_url"] = base_url
    if api_key:
        config["backend"]["api_key"] = api_key

    # Write config
    config_path.write_text(
        f"# AgentUX configuration — {provider_name}\n"
        f"# Docs: https://github.com/Rudrajmehta/AgentUX\n\n"
        + yaml.dump(config, default_flow_style=False, sort_keys=False)
    )
    console.print(f"\n[success]Config saved:[/] {config_path}")

    # Create monitors directory + sample
    monitors_dir = target / "monitors"
    monitors_dir.mkdir(exist_ok=True)

    sample_monitor = monitors_dir / "example-monitor.yaml"
    if not sample_monitor.exists():
        sample_monitor.write_text(
            "# Example monitor config\n"
            "name: homepage-pricing\n"
            "surface: browser\n"
            "target: https://example.com\n"
            "task: find pricing and contact information\n"
            'schedule: "0 */6 * * *"\n'
            f"backend: {config['backend']['name']}\n"
            f"model: {model}\n"
            "thresholds:\n"
            "  aes_drop_pct: 10\n"
            "  success_rate_min: 0.8\n"
            "  max_steps: 15\n"
        )

    # Ensure data dir
    data_dir = default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print()
    console.print("[bold]You're all set! Try:[/]")
    console.print()
    console.print("  agentux doctor                          [dim]# verify setup[/]")
    console.print(
        "  agentux run https://example.com --task 'find pricing'  [dim]# first real run[/]"
    )
    console.print("  agentux config                          [dim]# view config[/]")
    console.print("  agentux config set backend.model X      [dim]# change model[/]")
    console.print()
