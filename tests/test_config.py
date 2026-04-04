"""Tests for configuration."""

import tempfile
from pathlib import Path

from agentux.core.config import AgentUXConfig, load_config


def test_default_config():
    config = AgentUXConfig()
    assert config.max_steps == 25
    assert config.backend.name == "openai"
    assert config.browser.headless is True
    assert config.cli.timeout_seconds == 30


def test_config_ensure_dirs():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentUXConfig(data_dir=Path(tmpdir) / "agentux")
        config.ensure_dirs()
        assert (config.data_dir / "runs").exists()
        assert (config.data_dir / "monitors").exists()


def test_config_db_path():
    config = AgentUXConfig()
    assert "agentux.db" in str(config.db_path)


def test_config_database_url():
    config = AgentUXConfig()
    assert config.database_url.startswith("sqlite:///")


def test_load_config_from_yaml():
    with tempfile.TemporaryDirectory() as tmpdir:
        config_file = Path(tmpdir) / "test.yaml"
        config_file.write_text("max_steps: 42\nverbose: true\n")
        config = load_config(config_file)
        assert config.max_steps == 42
        assert config.verbose is True


def test_load_config_defaults():
    config = load_config()
    assert isinstance(config, AgentUXConfig)
