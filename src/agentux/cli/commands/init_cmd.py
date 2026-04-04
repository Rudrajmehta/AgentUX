"""agentux init — initialize AgentUX in a project."""

from __future__ import annotations

from pathlib import Path

import typer

from agentux.core.config import default_data_dir
from agentux.utils.branding import print_banner
from agentux.utils.console import console

app = typer.Typer()

DEFAULT_CONFIG = """# AgentUX configuration
# See: https://github.com/Rudrajmehta/AgentUX/blob/main/docs/monitoring.md

backend:
  name: openai
  model: gpt-4.1

browser:
  headless: true
  timeout_ms: 30000

cli:
  timeout_seconds: 30
  allow_network: false

max_steps: 25
"""


@app.callback(invoke_without_command=True)
def init(
    directory: str = typer.Argument(".", help="Directory to initialize in"),
) -> None:
    """Initialize AgentUX configuration in the current directory."""
    print_banner()

    target = Path(directory).resolve()
    target.mkdir(parents=True, exist_ok=True)
    config_path = target / ".agentux.yaml"

    if config_path.exists():
        console.print(f"[warning]Config already exists: {config_path}[/]")
        if not typer.confirm("Overwrite?"):
            raise typer.Exit()

    config_path.write_text(DEFAULT_CONFIG)
    console.print(f"[success]Created config:[/] {config_path}")

    # Create monitors directory
    monitors_dir = target / "monitors"
    monitors_dir.mkdir(exist_ok=True)

    sample_monitor = monitors_dir / "example-monitor.yaml"
    if not sample_monitor.exists():
        sample_monitor.write_text(
            """# Example monitor config
name: homepage-pricing
surface: browser
target: https://example.com
task: find pricing and contact information
schedule: "0 */6 * * *"
backend: openai
model: gpt-4.1
thresholds:
  aes_drop_pct: 10
  success_rate_min: 0.8
  max_steps: 15
"""
        )
        console.print(f"[success]Created example monitor:[/] {sample_monitor}")

    # Ensure data dir
    data_dir = default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    console.print()
    console.print("[bold]Next steps:[/]")
    console.print("  1. Edit .agentux.yaml with your settings")
    console.print("  2. Set OPENAI_API_KEY or ANTHROPIC_API_KEY (or use --demo)")
    console.print("  3. Run: agentux run https://example.com --task 'your task' --demo")
    console.print("  4. Run: agentux doctor to verify setup")
