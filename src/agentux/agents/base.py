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

TASK: {task}
TARGET: {target}

RULES — read carefully:
1. You have ZERO prior knowledge of this target. Discover everything from scratch.
2. Be EFFICIENT. Complete the task in as few steps as possible.
3. NEVER repeat an action you already took. If you read a section or extracted a fact, move on.
4. STOP as soon as you have enough information to answer the task. Set done=true immediately.
5. Do NOT exhaustively explore. Only visit what's needed for the task.
6. If you're stuck after 2-3 failed attempts, set done=true with a failure reason.
7. Each extracted_fact must be NEW information not already mentioned in previous steps.

Available actions:
{available_actions}

Current observation:
{observation}

{history_context}

Respond with a JSON object:
{{
  "thought_summary": "1-2 sentence reasoning",
  "action": "the action to take (or 'done' if task is complete)",
  "action_type": "navigate|click|type|execute|call_tool|read|search|scroll|done",
  "params": {{}},
  "extracted_facts": ["only NEW facts not already known"],
  "uncertainty": 0.0,
  "done": false,
  "done_reason": "if done, explain: success or failure"
}}

IMPORTANT: If you already have the answer to the task, set done=true RIGHT NOW."""


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
        """Given the current state, decide what action to take."""

    @abstractmethod
    async def close(self) -> None:
        """Clean up backend resources."""
