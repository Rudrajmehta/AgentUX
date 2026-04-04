"""OpenAI-compatible agent backend."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agentux.agents.base import SYSTEM_PROMPT_TEMPLATE, AgentBackend, AgentDecision
from agentux.core.config import BackendConfig
from agentux.core.exceptions import BackendAuthError, BackendError

logger = logging.getLogger(__name__)

AVAILABLE_ACTIONS = {
    "browser": (
        "- click(selector='.btn' OR text='Click me')\n"
        "- navigate(url='/pricing')\n"
        "- type(selector='input', text='query')\n"
        "- scroll(direction='down', amount=500)\n"
        "- back()\n"
        "- extract_text(selector='body')\n"
        "- done()"
    ),
    "markdown": (
        "- read_section(title='Getting Started')\n"
        "- search(query='pricing')\n"
        "- list_sections()\n"
        "- read_all()\n"
        "- done()"
    ),
    "cli": (
        "- execute(command='init my-project')\n"
        "- help(subcommand='init')\n"
        "- list_commands()\n"
        "- list_flags()\n"
        "- done()"
    ),
    "mcp": (
        "- call_tool(tool='tool_name', arguments={...})\n"
        "- list_tools()\n"
        "- inspect_tool(tool='tool_name')\n"
        "- done()"
    ),
}


class OpenAIBackend(AgentBackend):
    """Agent backend using OpenAI-compatible API."""

    name = "openai"

    def __init__(self, config: BackendConfig | None = None) -> None:
        self.config = config or BackendConfig()
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise BackendError(
                    "openai package not installed. Run: pip install openai"
                ) from None

            api_key = self.config.api_key or os.environ.get("OPENAI_API_KEY", "")
            if not api_key:
                raise BackendAuthError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                    "or configure backend.api_key in .agentux.yaml"
                )
            kwargs: dict[str, Any] = {"api_key": api_key, "timeout": self.config.timeout}
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            self._client = AsyncOpenAI(**kwargs)  # type: ignore[assignment]
        return self._client

    async def decide(
        self,
        task: str,
        target: str,
        surface_type: str,
        observation: str,
        available_actions: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentDecision:
        client = self._get_client()
        actions_desc = available_actions or AVAILABLE_ACTIONS.get(surface_type, "")

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            surface_type=surface_type,
            task=task,
            target=target,
            available_actions=actions_desc,
            observation=observation[:3000],
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            for step in history[-5:]:  # Last 5 steps for context
                messages.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "thought_summary": step.get("thought_summary", ""),
                                "action": step.get("action", ""),
                                "action_type": step.get("action_type", ""),
                            }
                        ),
                    }
                )
                if step.get("result"):
                    messages.append(
                        {
                            "role": "user",
                            "content": f"Result: {step['result'][:500]}",
                        }
                    )

        messages.append(
            {
                "role": "user",
                "content": "Decide the next action. Respond with valid JSON only.",
            }
        )

        try:
            response = await client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or "{}"
            tokens = response.usage.total_tokens if response.usage else 0

            data = json.loads(content)

            # Sanitize LLM output — coerce None to defaults
            facts = data.get("extracted_facts") or []
            if not isinstance(facts, list):
                facts = []

            params = data.get("params") or {}
            if not isinstance(params, dict):
                params = {}

            try:
                uncertainty = float(data.get("uncertainty") or 0.0)
            except (TypeError, ValueError):
                uncertainty = 0.5

            return AgentDecision(
                thought_summary=str(data.get("thought_summary") or ""),
                action=str(data.get("action") or ""),
                action_type=str(data.get("action_type") or ""),
                params=params,
                extracted_facts=[str(f) for f in facts],
                uncertainty=uncertainty,
                done=bool(data.get("done", False)),
                done_reason=str(data.get("done_reason") or ""),
                tokens_used=tokens,
            )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response: {e}")
            return AgentDecision(
                thought_summary="Failed to parse response",
                done=True,
                done_reason=f"JSON parse error: {e}",
            )
        except Exception as e:
            raise BackendError(f"OpenAI API error: {e}") from e

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
