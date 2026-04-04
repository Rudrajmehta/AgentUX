"""MCP (Model Context Protocol) surface adapter."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from agentux.core.config import MCPConfig
from agentux.core.exceptions import MCPSurfaceError
from agentux.core.models import Affordance, AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface

logger = logging.getLogger(__name__)


class MCPSurface(Surface):
    """Surface adapter for MCP server evaluation.

    Connects to an MCP server process, discovers tools, and evaluates
    how well tools can be discovered, understood, and used correctly.
    """

    surface_type = SurfaceType.MCP

    def __init__(self, target: str, config: MCPConfig | None = None) -> None:
        self.target = target  # MCP command or endpoint
        self.config = config or MCPConfig(command=target)
        self._process: asyncio.subprocess.Process | None = None
        self._tools: list[dict[str, Any]] = []
        self._affordances: list[Affordance] = []
        self._call_history: list[dict[str, Any]] = []
        self._request_id: int = 0
        self._stdin: asyncio.StreamWriter | None = None
        self._stdout: asyncio.StreamReader | None = None

    async def setup(self) -> None:
        command = self.config.command or self.target
        args = self.config.args

        try:
            self._process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**dict(__import__("os").environ), **self.config.env},
            )
            self._stdin = self._process.stdin
            self._stdout = self._process.stdout

            # Initialize MCP connection
            await self._send_request(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "agentux", "version": "0.1.0"},
                },
            )

            # Send initialized notification
            await self._send_notification("notifications/initialized", {})

        except FileNotFoundError:
            raise MCPSurfaceError(f"MCP command not found: {command}") from None
        except Exception as e:
            raise MCPSurfaceError(f"Failed to start MCP server: {e}") from e

    async def teardown(self) -> None:
        if self._process:
            try:
                if self._stdin:
                    self._stdin.close()
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except Exception:
                self._process.kill()

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self._stdin or not self._stdout:
            raise MCPSurfaceError("MCP server not connected")

        req_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        message = json.dumps(request) + "\n"
        self._stdin.write(message.encode())
        await self._stdin.drain()

        # Read response
        try:
            line = await asyncio.wait_for(
                self._stdout.readline(),
                timeout=self.config.timeout_seconds,
            )
            if not line:
                raise MCPSurfaceError("MCP server closed connection")
            response = json.loads(line.decode())
            return response.get("result", response)
        except TimeoutError:
            raise MCPSurfaceError(f"MCP request timed out: {method}") from None
        except json.JSONDecodeError as e:
            raise MCPSurfaceError(f"Invalid MCP response: {e}") from None

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self._stdin:
            raise MCPSurfaceError("MCP server not connected")

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        message = json.dumps(notification) + "\n"
        self._stdin.write(message.encode())
        await self._stdin.drain()

    async def discover(self) -> list[Affordance]:
        self._affordances = []
        try:
            result = await self._send_request("tools/list", {})
            tools = result.get("tools", []) if isinstance(result, dict) else []
            self._tools = tools

            for tool in tools:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "")
                schema = tool.get("inputSchema", {})
                properties = schema.get("properties", {})
                required = schema.get("required", [])

                self._affordances.append(
                    Affordance(
                        name=name,
                        kind="tool",
                        status=AffordanceStatus.DISCOVERED,
                        relevant=True,
                        notes=desc[:200],
                        metadata={
                            "description": desc,
                            "parameters": list(properties.keys()),
                            "required_params": required,
                            "schema": schema,
                        },
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to list MCP tools: {e}")

        return self._affordances

    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}

        if action == "call_tool":
            tool_name = params.get("tool", "")
            arguments = params.get("arguments", {})
            if not tool_name:
                return "Error: 'tool' parameter required"

            call_record = {
                "tool": tool_name,
                "arguments": arguments,
                "success": False,
                "result": "",
                "error": "",
            }

            try:
                result = await self._send_request(
                    "tools/call",
                    {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                )
                # Update affordance status
                for aff in self._affordances:
                    if aff.name == tool_name:
                        aff.status = AffordanceStatus.INTERACTED

                content = result.get("content", []) if isinstance(result, dict) else []
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                output = "\n".join(text_parts) if text_parts else str(result)
                call_record["success"] = True
                call_record["result"] = output[:2000]
                self._call_history.append(call_record)
                return output[:2000]

            except Exception as e:
                call_record["error"] = str(e)
                self._call_history.append(call_record)
                return f"Error calling tool '{tool_name}': {e}"

        elif action == "list_tools":
            if not self._tools:
                return "No tools discovered. Run discover() first."
            lines = []
            for tool in self._tools:
                name = tool.get("name", "unknown")
                desc = tool.get("description", "")[:80]
                lines.append(f"  {name}: {desc}")
            return "Available tools:\n" + "\n".join(lines)

        elif action == "inspect_tool":
            tool_name = params.get("tool", "")
            for tool in self._tools:
                if tool.get("name") == tool_name:
                    return json.dumps(tool, indent=2)[:2000]
            return f"Tool '{tool_name}' not found"

        else:
            return f"Unknown action: {action}. Available: call_tool, list_tools, inspect_tool"

    async def observe(self) -> str:
        parts = [
            f"MCP Server: {self.target}",
            f"Tools available: {len(self._tools)}",
            f"Tool calls made: {len(self._call_history)}",
        ]
        if self._tools:
            parts.append("\nAvailable tools:")
            for tool in self._tools:
                name = tool.get("name", "?")
                desc = tool.get("description", "")[:60]
                parts.append(f"  - {name}: {desc}")
        if self._call_history:
            last = self._call_history[-1]
            parts.append(f"\nLast call: {last['tool']}")
            parts.append(f"Success: {last['success']}")
        return "\n".join(parts)

    async def summarize_state(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type.value,
            "target": self.target,
            "tools_available": len(self._tools),
            "tools_called": len({c["tool"] for c in self._call_history}),
            "total_calls": len(self._call_history),
            "successful_calls": sum(1 for c in self._call_history if c["success"]),
            "failed_calls": sum(1 for c in self._call_history if not c["success"]),
            "tool_names": [t.get("name", "?") for t in self._tools],
        }

    async def list_affordances(self) -> list[Affordance]:
        return self._affordances
