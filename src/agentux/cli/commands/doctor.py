"""agentux doctor — diagnostics and health checks."""

from __future__ import annotations

import os
import shutil
import sys

import typer

from agentux.utils.branding import print_banner
from agentux.utils.console import console

app = typer.Typer()


def _check(label: str, ok: bool, detail: str = "") -> bool:
    icon = "[green]OK[/]" if ok else "[red]FAIL[/]"
    line = f"  {icon}  {label}"
    if detail:
        line += f"  [dim]({detail})[/]"
    console.print(line)
    return ok


def _info(label: str, detail: str = "") -> None:
    """Print an optional/informational check (not a pass/fail)."""
    line = f"  [yellow]--[/]  {label}"
    if detail:
        line += f"  [dim]({detail})[/]"
    console.print(line)


@app.callback(invoke_without_command=True)
def doctor() -> None:
    """Run diagnostics to verify AgentUX dependencies and configuration."""
    print_banner()
    console.print("[bold]Running diagnostics...[/]\n")

    all_ok = True

    # Python version
    v = sys.version_info
    all_ok &= _check(
        "Python 3.12+",
        v.major == 3 and v.minor >= 12,
        f"Python {v.major}.{v.minor}.{v.micro}",
    )

    # Core dependencies
    for pkg, name in [
        ("rich", "Rich"),
        ("typer", "Typer"),
        ("textual", "Textual"),
        ("pydantic", "Pydantic"),
        ("sqlalchemy", "SQLAlchemy"),
        ("yaml", "PyYAML"),
        ("httpx", "httpx"),
    ]:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "?")
            all_ok &= _check(name, True, f"v{ver}")
        except ImportError:
            all_ok &= _check(name, False, "not installed")

    # Playwright
    try:
        from importlib.metadata import version as pkg_version

        pw_ver = pkg_version("playwright")
        all_ok &= _check("Playwright", True, f"v{pw_ver}")
    except Exception:
        all_ok &= _check(
            "Playwright", False, "pip install playwright && playwright install chromium"
        )

    # Playwright browsers
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        all_ok &= _check("Chromium browser", True, "available")
    except Exception:
        all_ok &= _check("Chromium browser", False, "run: playwright install chromium")

    # API keys — these are OPTIONAL, not failures
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    if has_openai:
        _check("OpenAI API key", True, "OPENAI_API_KEY set")
    else:
        _info("OpenAI API key", "not set — use --demo for mock runs, or set OPENAI_API_KEY")

    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if has_anthropic:
        _check("Anthropic API key", True, "ANTHROPIC_API_KEY set")
    else:
        _info("Anthropic API key", "not set — optional, set ANTHROPIC_API_KEY to use")

    # Data directory
    from agentux.core.config import default_data_dir

    data_dir = default_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        all_ok &= _check("Data directory", True, str(data_dir))
    except Exception as e:
        all_ok &= _check("Data directory", False, str(e))

    # SQLite
    try:
        import sqlite3

        all_ok &= _check("SQLite", True, f"v{sqlite3.sqlite_version}")
    except Exception:
        all_ok &= _check("SQLite", False, "not available")

    # Terminal
    cols = shutil.get_terminal_size().columns
    all_ok &= _check("Terminal width", cols >= 80, f"{cols} columns")

    console.print()
    if all_ok:
        console.print("[bold green]All checks passed![/] You're ready to go.\n")
        if not has_openai and not has_anthropic:
            console.print("  [dim]No API key set. Use --demo to run with mock backend:[/]")
            console.print("  agentux run https://example.com --task 'find pricing' --demo\n")
        else:
            console.print("  [dim]Try:[/] agentux run https://example.com --task 'find pricing'\n")
    else:
        console.print("[bold yellow]Some checks failed.[/] Fix the issues above and run again.")
        console.print("  [dim]Tip:[/] Use --demo flag to run without API keys.\n")
