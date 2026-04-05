"""Sandboxing utilities for safe CLI execution."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from agentux.core.exceptions import SandboxError


class Sandbox:
    """A temporary sandboxed directory for safe CLI execution."""

    def __init__(self, prefix: str = "agentux-sandbox-") -> None:
        self._prefix = prefix
        self._tmpdir: Path | None = None

    @property
    def path(self) -> Path:
        if self._tmpdir is None:
            raise SandboxError("Sandbox not initialized. Call enter() first.")
        return self._tmpdir

    def enter(self) -> Path:
        self._tmpdir = Path(tempfile.mkdtemp(prefix=self._prefix))
        return self._tmpdir

    def exit(self) -> None:
        if self._tmpdir and self._tmpdir.exists():
            shutil.rmtree(self._tmpdir, ignore_errors=True)
            self._tmpdir = None

    def __enter__(self) -> Path:
        return self.enter()

    def __exit__(self, *args: object) -> None:
        self.exit()


BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "> /dev/sda",
    "sudo rm",
    "chmod -R 777 /",
]

# Patterns that detect piped-to-shell execution (curl/wget ... | sh/bash)
_PIPE_TO_SHELL_KEYWORDS = [
    ("curl", "| sh"),
    ("curl", "| bash"),
    ("wget", "| sh"),
    ("wget", "| bash"),
]


def is_command_safe(command: str, extra_blocked: list[str] | None = None) -> tuple[bool, str]:
    """Check if a CLI command is safe to execute in sandbox."""
    cmd_lower = command.strip().lower()
    all_blocked = BLOCKED_PATTERNS + (extra_blocked or [])
    for pattern in all_blocked:
        if pattern.lower() in cmd_lower:
            return False, f"Blocked pattern detected: {pattern}"

    # Detect pipe-to-shell patterns (curl ... | bash, wget ... | sh)
    for source, sink in _PIPE_TO_SHELL_KEYWORDS:
        if source in cmd_lower and sink in cmd_lower:
            return False, f"Blocked pattern detected: {source} ... {sink}"

    return True, ""


def create_sandbox_env(sandbox_path: Path, allow_network: bool = False) -> dict[str, str]:
    """Create a restricted environment for sandboxed execution.

    Passes through the real HOME (for tool configs like ~/.mem0, ~/.npmrc)
    and all API key env vars. The sandbox_path is used as the working
    directory, not as HOME — tools need their real config files.
    """
    env = {
        "HOME": os.environ.get("HOME", str(sandbox_path)),
        "TMPDIR": str(sandbox_path / "tmp"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }
    (sandbox_path / "tmp").mkdir(exist_ok=True)

    # Pass through API keys and common tool credentials
    for key in os.environ:
        if any(
            key.endswith(suffix) or key.startswith(prefix)
            for suffix in ("_API_KEY", "_TOKEN", "_SECRET", "_KEY")
            for prefix in ("MEM0_", "OPENAI_", "ANTHROPIC_", "GROQ_", "npm_", "NODE_", "XDG_")
        ):
            env[key] = os.environ[key]
    if not allow_network:
        # Signal to child processes (convention, not enforcement)
        env["AGENTUX_SANDBOX"] = "1"
        env["NO_PROXY"] = "*"
    return env
