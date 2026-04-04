"""CLI surface adapter for command-line tool evaluation."""

from __future__ import annotations

import asyncio
import logging
import shutil
from typing import Any

from agentux.core.config import CLIConfig
from agentux.core.exceptions import CLISurfaceError
from agentux.core.models import Affordance, AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface
from agentux.utils.sandbox import Sandbox, create_sandbox_env, is_command_safe

logger = logging.getLogger(__name__)


class CLISurface(Surface):
    """Surface adapter for evaluating CLI tools."""

    surface_type = SurfaceType.CLI

    def __init__(self, target: str, config: CLIConfig | None = None) -> None:
        self.target = target  # The CLI command/binary name
        self.config = config or CLIConfig()
        self._sandbox = Sandbox()
        self._sandbox_path = None
        self._affordances: list[Affordance] = []
        self._command_history: list[dict[str, Any]] = []
        self._discovered_commands: set[str] = set()
        self._discovered_flags: set[str] = set()

    async def setup(self) -> None:
        binary = shutil.which(self.target)
        if not binary:
            raise CLISurfaceError(
                f"CLI tool '{self.target}' not found in PATH. "
                f"Make sure it's installed and accessible."
            )
        self._sandbox_path = self._sandbox.enter()

    async def teardown(self) -> None:
        self._sandbox.exit()

    async def _run_command(self, command: str) -> dict[str, Any]:
        """Execute a command in the sandbox and capture output."""
        safe, reason = is_command_safe(command, self.config.blocked_commands)
        if not safe:
            return {
                "command": command,
                "stdout": "",
                "stderr": f"BLOCKED: {reason}",
                "exit_code": -1,
                "blocked": True,
            }

        env = create_sandbox_env(self._sandbox_path, self.config.allow_network)
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._sandbox_path),
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.timeout_seconds,
            )
            result = {
                "command": command,
                "stdout": stdout.decode("utf-8", errors="replace")[
                    : self.config.max_output_lines * 80
                ],
                "stderr": stderr.decode("utf-8", errors="replace")[:2000],
                "exit_code": proc.returncode or 0,
                "blocked": False,
            }
        except asyncio.TimeoutError:
            result = {
                "command": command,
                "stdout": "",
                "stderr": f"Command timed out after {self.config.timeout_seconds}s",
                "exit_code": -1,
                "blocked": False,
            }
        except Exception as e:
            result = {
                "command": command,
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "blocked": False,
            }

        self._command_history.append(result)
        return result

    async def discover(self) -> list[Affordance]:
        self._affordances = []

        # Run --help to discover commands and flags
        for flag in ["--help", "-h", "help"]:
            result = await self._run_command(f"{self.target} {flag}")
            if result["exit_code"] == 0 and result["stdout"]:
                self._parse_help_output(result["stdout"])
                break

        # Try --version
        for flag in ["--version", "-V", "version"]:
            result = await self._run_command(f"{self.target} {flag}")
            if result["exit_code"] == 0:
                break

        return self._affordances

    def _parse_help_output(self, text: str) -> None:
        """Extract commands and flags from help text."""
        import re

        lines = text.split("\n")
        in_commands = False
        in_options = False

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()

            if any(kw in lower for kw in ["commands:", "subcommands:", "available commands"]):
                in_commands = True
                in_options = False
                continue
            if any(kw in lower for kw in ["options:", "flags:", "arguments:"]):
                in_options = True
                in_commands = False
                continue
            if not stripped or stripped.startswith("---"):
                in_commands = False
                in_options = False
                continue

            if in_commands:
                match = re.match(r"\s{2,}(\w[\w-]*)\s*(.*)", line)
                if match:
                    cmd_name = match.group(1)
                    desc = match.group(2).strip()
                    self._discovered_commands.add(cmd_name)
                    self._affordances.append(
                        Affordance(
                            name=cmd_name,
                            kind="command",
                            status=AffordanceStatus.DISCOVERED,
                            relevant=True,
                            notes=desc[:100],
                        )
                    )

            if in_options:
                match = re.match(r"\s{2,}(-[\w-]+(?:,\s*--[\w-]+)?)\s*(.*)", line)
                if match:
                    flag_name = match.group(1).strip()
                    desc = match.group(2).strip()
                    self._discovered_flags.add(flag_name)
                    self._affordances.append(
                        Affordance(
                            name=flag_name,
                            kind="flag",
                            status=AffordanceStatus.DISCOVERED,
                            relevant=True,
                            notes=desc[:100],
                        )
                    )

    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}

        if action == "execute":
            command = params.get("command", "")
            if not command:
                return "Error: 'command' parameter required"
            # Prepend target if the command doesn't start with it
            if not command.startswith(self.target):
                command = f"{self.target} {command}"
            result = await self._run_command(command)
            output = result["stdout"]
            if result["stderr"]:
                output += f"\nSTDERR: {result['stderr']}"
            output += f"\nExit code: {result['exit_code']}"
            return output

        elif action == "help":
            subcommand = params.get("subcommand", "")
            cmd = f"{self.target} {subcommand} --help" if subcommand else f"{self.target} --help"
            result = await self._run_command(cmd)
            return result["stdout"] or result["stderr"] or "No help output"

        elif action == "list_commands":
            return "\n".join(sorted(self._discovered_commands)) or "No commands discovered yet"

        elif action == "list_flags":
            return "\n".join(sorted(self._discovered_flags)) or "No flags discovered yet"

        else:
            return f"Unknown action: {action}. Available: execute, help, list_commands, list_flags"

    async def observe(self) -> str:
        parts = [
            f"CLI Tool: {self.target}",
            f"Sandbox: {self._sandbox_path}",
            f"Commands discovered: {len(self._discovered_commands)}",
            f"Flags discovered: {len(self._discovered_flags)}",
            f"Commands executed: {len(self._command_history)}",
        ]
        if self._command_history:
            last = self._command_history[-1]
            parts.append(f"\nLast command: {last['command']}")
            parts.append(f"Exit code: {last['exit_code']}")
            if last["stdout"]:
                parts.append(f"Output:\n{last['stdout'][:1000]}")
        return "\n".join(parts)

    async def summarize_state(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type.value,
            "target": self.target,
            "commands_discovered": len(self._discovered_commands),
            "flags_discovered": len(self._discovered_flags),
            "commands_executed": len(self._command_history),
            "successful_commands": sum(
                1 for c in self._command_history if c["exit_code"] == 0
            ),
            "failed_commands": sum(
                1 for c in self._command_history if c["exit_code"] != 0
            ),
        }

    async def list_affordances(self) -> list[Affordance]:
        return self._affordances
