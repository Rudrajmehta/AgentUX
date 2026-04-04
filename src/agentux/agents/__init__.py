"""Agent backends for LLM-driven evaluation."""

from agentux.agents.base import AgentBackend
from agentux.agents.mock import MockBackend

__all__ = ["AgentBackend", "MockBackend"]
