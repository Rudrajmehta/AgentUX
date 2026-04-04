"""agentux export — export run data."""

from __future__ import annotations

from pathlib import Path

import typer

from agentux.core.config import load_config
from agentux.storage.database import Database
from agentux.utils.console import console

app = typer.Typer()


@app.callback(invoke_without_command=True)
def export(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, markdown, csv"),
    output: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export a run as JSON, Markdown, or CSV."""
    config = load_config()
    config.ensure_dirs()
    db = Database(config.database_url)

    trace = db.get_run(run_id)
    if not trace:
        console.print(f"[error]Run '{run_id}' not found.[/]")
        raise typer.Exit(1)

    analysis = db.get_run_analysis(run_id)

    if format == "json":
        from agentux.export.json_export import export_json

        content = export_json(trace, analysis)
    elif format == "markdown":
        from agentux.export.markdown_export import export_markdown

        content = export_markdown(trace, analysis)
    elif format == "csv":
        from agentux.export.csv_export import export_csv

        content = export_csv(trace)
    else:
        console.print(f"[error]Unknown format: {format}. Use json, markdown, or csv.[/]")
        raise typer.Exit(1)

    if output:
        path = Path(output)
        path.write_text(content)
        console.print(f"[success]Exported to {path}[/]")
    else:
        console.print(content)
