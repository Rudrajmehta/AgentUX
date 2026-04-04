"""Anthropic-compatible agent backend."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agentux.agents.base import SYSTEM_PROMPT_TEMPLATE, AgentBackend, AgentDecision
from agentux.agents.openai_backend import AVAILABLE_ACTIONS
from agentux.core.config import BackendConfig
from agentux.core.exceptions import BackendAuthError, BackendError

logger = logging.getLogger(__name__)


class AnthropicBackend(AgentBackend):
    """Agent backend using Anthropic API."""

    name = "anthropic"

    def __init__(self, config: BackendConfig | None = None) -> None:
        self.config = config or BackendConfig(name="anthropic", model="claude-sonnet-4-20250514")
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise BackendError(
                    "anthropic package not installed. Run: pip install anthropic"
                ) from None

            api_key = self.config.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise BackendAuthError(
                    "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                    "or configure backend.api_key in .agentux.yaml"
                )
            self._client = AsyncAnthropic(api_key=api_key, timeout=self.config.timeout)  # type: ignore[assignment]
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

        messages: list[dict[str, Any]] = []

        if history:
            for step in history[-5:]:
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
            response = await client.messages.create(
                model=self.config.model,
                system=system_prompt,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            tokens = (
                (response.usage.input_tokens + response.usage.output_tokens)
                if response.usage
                else 0
            )

            # Extract JSON from response (may be wrapped in markdown)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

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
            logger.warning(f"Failed to parse Anthropic response: {e}")
            return AgentDecision(
                thought_summary="Failed to parse response",
                done=True,
                done_reason=f"JSON parse error: {e}",
            )
        except Exception as e:
            raise BackendError(f"Anthropic API error: {e}") from e

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
