"""Abstract base class for agent backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    """A decision made by the agent backend."""

    thought_summary: str = ""
    action: str = ""
    action_type: str = ""  # navigate, click, type, execute, call_tool, read, search, done
    params: dict[str, Any] = Field(default_factory=dict)
    extracted_facts: list[str] = Field(default_factory=list)
    uncertainty: float = 0.0  # 0-1
    done: bool = False
    done_reason: str | None = ""
    tokens_used: int = 0


SYSTEM_PROMPT_TEMPLATE = """You are an AI agent evaluating the usability of a {surface_type}.

Your task: {task}

Target: {target}

You have NO prior knowledge of this target. You must discover everything from scratch.

Available actions for this surface:
{available_actions}

Current observation:
{observation}

Respond with a JSON object containing:
- thought_summary: Brief reasoning about what to do next (1-2 sentences max)
- action: The action to take
- action_type: The type of action (navigate, click, type, execute, call_tool, read, search, done)
- params: Parameters for the action (dict)
- extracted_facts: Any useful facts learned from the current observation (list of strings)
- uncertainty: How uncertain you are about this action (0.0 to 1.0)
- done: Whether the task is complete (true/false)
- done_reason: If done, why (success or failure reason)

Be efficient. Do not explore exhaustively. Focus on completing the task.
If stuck after a few attempts, mark done with failure reason.
"""


class AgentBackend(ABC):
    """Base interface for LLM agent backends.

    Extension point: Future harness integrations (e.g., LangChain, CrewAI)
    should implement this interface to plug into AgentUX.
    """

    name: str = "base"

    @abstractmethod
    async def decide(
        self,
        task: str,
        target: str,
        surface_type: str,
        observation: str,
        available_actions: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentDecision:
        """Given the current state, decide what action to take.

        Args:
            task: The task the agent should complete.
            target: The target URL/command/endpoint.
            surface_type: Type of surface (browser, markdown, cli, mcp).
            observation: Current state observation from the surface.
            available_actions: Description of available actions.
            history: Previous steps in this run (summaries only, no raw CoT).

        Returns:
            An AgentDecision with the next action to take.
        """

    @abstractmethod
    async def close(self) -> None:
        """Clean up backend resources."""
