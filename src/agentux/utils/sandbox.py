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
    "curl | sh",
    "curl | bash",
    "wget | sh",
    "wget | bash",
]


def is_command_safe(command: str, extra_blocked: list[str] | None = None) -> tuple[bool, str]:
    """Check if a CLI command is safe to execute in sandbox."""
    cmd_lower = command.strip().lower()
    all_blocked = BLOCKED_PATTERNS + (extra_blocked or [])
    for pattern in all_blocked:
        if pattern.lower() in cmd_lower:
            return False, f"Blocked pattern detected: {pattern}"
    return True, ""


def create_sandbox_env(sandbox_path: Path, allow_network: bool = False) -> dict[str, str]:
    """Create a restricted environment for sandboxed execution."""
    env = {
        "HOME": str(sandbox_path),
        "TMPDIR": str(sandbox_path / "tmp"),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    }
    (sandbox_path / "tmp").mkdir(exist_ok=True)
    if not allow_network:
        # Signal to child processes (convention, not enforcement)
        env["AGENTUX_SANDBOX"] = "1"
        env["NO_PROXY"] = "*"
    return env
