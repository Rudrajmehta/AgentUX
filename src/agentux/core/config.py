"""AgentUX configuration management."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_data_dir
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


def default_data_dir() -> Path:
    return Path(user_data_dir("agentux", "agentux"))


class BackendConfig(BaseModel):
    """LLM backend configuration."""

    name: str = "openai"
    model: str = "gpt-4.1"
    api_key: str = ""  # resolved from env if empty
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    timeout: float = 60.0


class BrowserConfig(BaseModel):
    """Browser surface configuration."""

    headless: bool = True
    timeout_ms: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 720
    screenshots: bool = False
    screenshot_dir: str = ""


class CLIConfig(BaseModel):
    """CLI surface configuration."""

    shell: str = "/bin/bash"
    timeout_seconds: int = 30
    max_output_lines: int = 500
    sandbox_dir: str = ""
    allow_network: bool = False
    allowed_commands: list[str] = Field(default_factory=list)
    blocked_commands: list[str] = Field(
        default_factory=lambda: ["rm -rf /", "sudo", "mkfs", "dd if="]
    )


class MCPConfig(BaseModel):
    """MCP surface configuration."""

    command: str = ""
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30


class StorageConfig(BaseModel):
    """Storage layer configuration."""

    database_url: str = ""  # defaults to sqlite in data_dir
    max_runs: int = 10000


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    enabled: bool = True
    max_concurrent: int = 2


class AlertConfig(BaseModel):
    """Alert delivery configuration."""

    slack_webhook: str = ""
    discord_webhook: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_to: list[str] = Field(default_factory=list)


class AgentUXConfig(BaseSettings):
    """Root configuration for AgentUX."""

    data_dir: Path = Field(default_factory=default_data_dir)
    backend: BackendConfig = Field(default_factory=BackendConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    cli: CLIConfig = Field(default_factory=CLIConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    alerts: AlertConfig = Field(default_factory=AlertConfig)
    max_steps: int = 25
    verbose: bool = False
    demo_mode: bool = False

    model_config = {"env_prefix": "AGENTUX_", "env_nested_delimiter": "__"}

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "runs").mkdir(exist_ok=True)
        (self.data_dir / "monitors").mkdir(exist_ok=True)
        (self.data_dir / "exports").mkdir(exist_ok=True)
        (self.data_dir / "screenshots").mkdir(exist_ok=True)

    @property
    def db_path(self) -> Path:
        return self.data_dir / "agentux.db"

    @property
    def database_url(self) -> str:
        if self.storage.database_url:
            return self.storage.database_url
        return f"sqlite:///{self.db_path}"


def load_config(config_path: Path | None = None) -> AgentUXConfig:
    """Load config from YAML file, env vars, and defaults."""
    if config_path and config_path.exists():
        raw = yaml.safe_load(config_path.read_text()) or {}
        return AgentUXConfig(**raw)
    # Check default locations
    for candidate in [
        Path.cwd() / ".agentux.yaml",
        Path.cwd() / ".agentux.yml",
        Path.home() / ".config" / "agentux" / "config.yaml",
    ]:
        if candidate.exists():
            raw = yaml.safe_load(candidate.read_text()) or {}
            return AgentUXConfig(**raw)
    return AgentUXConfig()


def load_monitor_config(path: Path) -> dict[str, Any]:
    """Load a monitor YAML config file."""
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid monitor config: {path}")
    return raw
