"""Tests for agent backends."""

from __future__ import annotations

import pytest

from agentux.agents.base import AgentBackend, AgentDecision
from agentux.agents.mock import MOCK_SEQUENCES, MockBackend


class TestAgentDecision:
    def test_defaults(self) -> None:
        d = AgentDecision()
        assert d.thought_summary == ""
        assert d.action == ""
        assert d.action_type == ""
        assert d.done is False
        assert d.uncertainty == 0.0
        assert d.tokens_used == 0
        assert d.params == {}
        assert d.extracted_facts == []

    def test_with_values(self) -> None:
        d = AgentDecision(
            thought_summary="Navigate to pricing",
            action="click",
            action_type="click",
            params={"selector": "#pricing"},
            extracted_facts=["Found pricing link"],
            uncertainty=0.2,
            done=False,
            tokens_used=450,
        )
        assert d.thought_summary == "Navigate to pricing"
        assert d.params["selector"] == "#pricing"
        assert len(d.extracted_facts) == 1

    def test_done_decision(self) -> None:
        d = AgentDecision(
            action="done",
            action_type="done",
            done=True,
            done_reason="Task completed successfully",
        )
        assert d.done is True
        assert "successfully" in d.done_reason


class TestMockBackend:
    @pytest.fixture
    def backend(self) -> MockBackend:
        return MockBackend()

    async def test_name(self, backend: MockBackend) -> None:
        assert backend.name == "mock"

    async def test_browser_sequence(self, backend: MockBackend) -> None:
        """Mock backend should replay the browser sequence in order."""
        decisions = []
        for _ in range(10):
            d = await backend.decide(
                task="Find pricing",
                target="https://example.com",
                surface_type="browser",
                observation="page content",
                available_actions="click, read, done",
            )
            decisions.append(d)
            if d.done:
                break

        assert len(decisions) >= 2
        assert decisions[-1].done is True
        # First step should be read
        assert decisions[0].action_type == "read"

    async def test_markdown_sequence(self, backend: MockBackend) -> None:
        decisions = []
        for _ in range(10):
            d = await backend.decide(
                task="Find setup instructions",
                target="README.md",
                surface_type="markdown",
                observation="document content",
                available_actions="read_section, search, done",
            )
            decisions.append(d)
            if d.done:
                break

        assert decisions[-1].done is True

    async def test_cli_sequence(self, backend: MockBackend) -> None:
        decisions = []
        for _ in range(10):
            d = await backend.decide(
                task="Create project",
                target="mypackager",
                surface_type="cli",
                observation="CLI output",
                available_actions="execute, help, done",
            )
            decisions.append(d)
            if d.done:
                break

        assert decisions[-1].done is True
        # Should include at least one execute step
        action_types = [d.action_type for d in decisions]
        assert "execute" in action_types

    async def test_mcp_sequence(self, backend: MockBackend) -> None:
        decisions = []
        for _ in range(10):
            d = await backend.decide(
                task="Search data",
                target="test-server",
                surface_type="mcp",
                observation="tools list",
                available_actions="list_tools, call_tool, done",
            )
            decisions.append(d)
            if d.done:
                break

        assert decisions[-1].done is True
        action_types = [d.action_type for d in decisions]
        assert "tool_call" in action_types

    async def test_unknown_surface_falls_back_to_browser(self, backend: MockBackend) -> None:
        d = await backend.decide(
            task="t",
            target="t",
            surface_type="unknown_surface",
            observation="",
            available_actions="",
        )
        # Should fall back to browser sequence
        assert d.action_type in ("read", "click", "done")

    async def test_exhausted_sequence_returns_done(self, backend: MockBackend) -> None:
        """After all scripted steps, backend returns done."""
        for _ in range(20):
            d = await backend.decide(
                task="t",
                target="t",
                surface_type="browser",
                observation="",
                available_actions="",
            )
        assert d.done is True
        assert "complete" in d.done_reason.lower()

    async def test_tokens_are_set(self, backend: MockBackend) -> None:
        d = await backend.decide(
            task="t",
            target="t",
            surface_type="browser",
            observation="",
            available_actions="",
        )
        assert d.tokens_used > 0

    async def test_close_resets_index(self, backend: MockBackend) -> None:
        await backend.decide(
            task="t",
            target="t",
            surface_type="browser",
            observation="",
            available_actions="",
        )
        assert backend._step_index == 1
        await backend.close()
        assert backend._step_index == 0

    async def test_extracted_facts(self, backend: MockBackend) -> None:
        d = await backend.decide(
            task="t",
            target="t",
            surface_type="browser",
            observation="",
            available_actions="",
        )
        assert isinstance(d.extracted_facts, list)

    def test_mock_sequences_exist_for_all_surfaces(self) -> None:
        assert "browser" in MOCK_SEQUENCES
        assert "markdown" in MOCK_SEQUENCES
        assert "cli" in MOCK_SEQUENCES
        assert "mcp" in MOCK_SEQUENCES

    def test_each_sequence_ends_with_done(self) -> None:
        for surface, seq in MOCK_SEQUENCES.items():
            assert seq[-1].get("done") is True, f"{surface} sequence doesn't end with done"


class TestAgentBackendABC:
    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            AgentBackend()  # type: ignore[abstract]
