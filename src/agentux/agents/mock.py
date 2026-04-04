"""Mock agent backend for testing and demo mode."""

from __future__ import annotations

from typing import Any

from agentux.agents.base import AgentBackend, AgentDecision

# Scripted demo sequences for each surface type
MOCK_SEQUENCES: dict[str, list[dict[str, Any]]] = {
    "browser": [
        {
            "thought_summary": "Let me observe the page structure first",
            "action": "extract_text",
            "action_type": "read",
            "params": {"selector": "body"},
            "extracted_facts": ["This appears to be a product homepage"],
        },
        {
            "thought_summary": "Looking for navigation to find pricing",
            "action": "click",
            "action_type": "click",
            "params": {"text": "Pricing"},
            "extracted_facts": ["Found navigation with Pricing link"],
        },
        {
            "thought_summary": "Reading pricing page content",
            "action": "extract_text",
            "action_type": "read",
            "params": {"selector": "main"},
            "extracted_facts": ["Found pricing tiers: Free, Pro, Enterprise"],
        },
        {
            "thought_summary": "Looking for enterprise contact information",
            "action": "click",
            "action_type": "click",
            "params": {"text": "Contact"},
            "extracted_facts": ["Enterprise contact form found"],
        },
        {
            "thought_summary": "Task complete - found pricing and contact",
            "action": "done",
            "action_type": "done",
            "params": {},
            "extracted_facts": ["Pricing: Free/Pro/Enterprise", "Contact: sales@example.com"],
            "done": True,
            "done_reason": "Successfully found pricing tiers and enterprise contact",
        },
    ],
    "markdown": [
        {
            "thought_summary": "List document sections to understand structure",
            "action": "list_sections",
            "action_type": "read",
            "params": {},
            "extracted_facts": ["Document has clear heading structure"],
        },
        {
            "thought_summary": "Search for setup instructions",
            "action": "search",
            "action_type": "search",
            "params": {"query": "setup"},
            "extracted_facts": ["Found setup section with installation steps"],
        },
        {
            "thought_summary": "Read the getting started section in detail",
            "action": "read_section",
            "action_type": "read",
            "params": {"title": "Getting Started"},
            "extracted_facts": ["Clear step-by-step instructions provided"],
        },
        {
            "thought_summary": "Task complete - understood setup instructions",
            "action": "done",
            "action_type": "done",
            "params": {},
            "extracted_facts": ["Setup requires: install, configure, run"],
            "done": True,
            "done_reason": "Successfully understood setup instructions",
        },
    ],
    "cli": [
        {
            "thought_summary": "First check help text to discover commands",
            "action": "help",
            "action_type": "read",
            "params": {},
            "extracted_facts": ["CLI has init, add, remove, run commands"],
        },
        {
            "thought_summary": "Create a new project",
            "action": "execute",
            "action_type": "execute",
            "params": {"command": "init my-project"},
            "extracted_facts": ["Project initialized successfully"],
        },
        {
            "thought_summary": "Check help for add command",
            "action": "help",
            "action_type": "read",
            "params": {"subcommand": "add"},
            "extracted_facts": ["add command takes package name as argument"],
        },
        {
            "thought_summary": "Add a dependency",
            "action": "execute",
            "action_type": "execute",
            "params": {"command": "add requests"},
            "extracted_facts": ["Dependency added to project"],
        },
        {
            "thought_summary": "Task complete",
            "action": "done",
            "action_type": "done",
            "params": {},
            "extracted_facts": ["Project created, dependency added"],
            "done": True,
            "done_reason": "Successfully created project and added dependency",
        },
    ],
    "mcp": [
        {
            "thought_summary": "List available tools",
            "action": "list_tools",
            "action_type": "read",
            "params": {},
            "extracted_facts": ["Server has 5 tools available"],
        },
        {
            "thought_summary": "Inspect the most relevant tool",
            "action": "inspect_tool",
            "action_type": "read",
            "params": {"tool": "search"},
            "extracted_facts": ["search tool takes query parameter"],
        },
        {
            "thought_summary": "Call the search tool",
            "action": "call_tool",
            "action_type": "tool_call",
            "params": {"tool": "search", "arguments": {"query": "test"}},
            "extracted_facts": ["Tool returned relevant results"],
        },
        {
            "thought_summary": "Task complete - tool discovered and used",
            "action": "done",
            "action_type": "done",
            "params": {},
            "extracted_facts": ["Correct tool selected and used successfully"],
            "done": True,
            "done_reason": "Successfully discovered and used the correct tool",
        },
    ],
}


class MockBackend(AgentBackend):
    """Mock backend that replays scripted sequences for testing/demos."""

    name = "mock"

    def __init__(self) -> None:
        self._step_index: int = 0
        self._surface_type: str = "browser"

    async def decide(
        self,
        task: str,
        target: str,
        surface_type: str,
        observation: str,
        available_actions: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentDecision:
        self._surface_type = surface_type
        sequence = MOCK_SEQUENCES.get(surface_type, MOCK_SEQUENCES["browser"])

        if self._step_index >= len(sequence):
            return AgentDecision(
                thought_summary="No more scripted steps",
                action="done",
                action_type="done",
                done=True,
                done_reason="Mock sequence complete",
                tokens_used=250,
            )

        step = sequence[self._step_index]
        step_idx = self._step_index
        self._step_index += 1

        # Deterministic tokens based on step position (no randomness)
        tokens = 300 + step_idx * 50

        return AgentDecision(
            thought_summary=step.get("thought_summary", ""),
            action=step.get("action", "done"),
            action_type=step.get("action_type", "read"),
            params=step.get("params", {}),
            extracted_facts=step.get("extracted_facts", []),
            uncertainty=0.1 + step_idx * 0.05,  # Deterministic, increasing
            done=step.get("done", False),
            done_reason=step.get("done_reason", ""),
            tokens_used=tokens,
        )

    async def close(self) -> None:
        self._step_index = 0
