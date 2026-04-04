"""Core run orchestrator — connects surfaces, agents, analyzers, and scoring."""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any

from agentux.agents.base import AgentBackend
from agentux.analyzers.pipeline import AnalyzerPipeline
from agentux.core.config import AgentUXConfig
from agentux.core.models import RunStatus, RunTrace, StepRecord, SurfaceType
from agentux.scoring.engine import ScoringEngine
from agentux.surfaces.base import Surface

logger = logging.getLogger(__name__)


class RunCallback:
    """Callback interface for live run updates (used by TUI/CLI)."""

    def on_step_start(self, step_number: int, trace: RunTrace) -> None:
        pass

    def on_step_complete(self, step: StepRecord, trace: RunTrace) -> None:
        pass

    def on_run_complete(self, trace: RunTrace, analysis: dict[str, Any]) -> None:
        pass

    def on_error(self, error: str, trace: RunTrace) -> None:
        pass


class Runner:
    """Orchestrates a single benchmark run."""

    def __init__(
        self,
        config: AgentUXConfig,
        callback: RunCallback | None = None,
    ) -> None:
        self.config = config
        self.callback = callback or RunCallback()
        self.scoring = ScoringEngine()
        self.pipeline = AnalyzerPipeline()

    async def run(
        self,
        surface: Surface,
        backend: AgentBackend,
        task: str,
        target: str,
        max_steps: int | None = None,
        tags: list[str] | None = None,
    ) -> tuple[RunTrace, dict[str, Any]]:
        """Execute a complete benchmark run.

        Returns:
            Tuple of (RunTrace, analysis_dict)
        """
        max_steps = max_steps or self.config.max_steps

        trace = RunTrace(
            surface_type=surface.surface_type,
            target=target,
            task=task,
            model=getattr(self.config.backend, "model", ""),
            backend=getattr(backend, "name", "unknown"),
            status=RunStatus.RUNNING,
            tags=tags or [],
        )

        try:
            # Setup surface
            await surface.setup()

            # Initial discovery
            affordances = await surface.discover()
            trace.affordances = affordances

            # Agent interaction loop
            history: list[dict[str, Any]] = []

            for step_num in range(1, max_steps + 1):
                self.callback.on_step_start(step_num, trace)
                step_start = time.time()

                # Observe current state
                observation = await surface.observe()

                # Get available actions description
                from agentux.agents.openai_backend import AVAILABLE_ACTIONS

                available_actions = AVAILABLE_ACTIONS.get(surface.surface_type.value, "")

                # Agent decides
                decision = await backend.decide(
                    task=task,
                    target=target,
                    surface_type=surface.surface_type.value,
                    observation=observation,
                    available_actions=available_actions,
                    history=history,
                )

                step_latency = (time.time() - step_start) * 1000

                # Execute action on surface
                result = ""
                success = True
                errors: list[str] = []

                if decision.done:
                    result = decision.done_reason or ""
                else:
                    try:
                        result = await surface.act(decision.action, decision.params)
                        # Detect failure signals in result text
                        result_lower = result.lower()
                        if (
                            result.startswith("Error")
                            or "not found" in result_lower
                            or "error:" in result_lower[:50]
                            or "failed" in result_lower[:50]
                            or "blocked" in result_lower[:50]
                            or "unknown action" in result_lower
                        ):
                            success = False
                            errors.append(result[:200])
                    except Exception as e:
                        result = str(e)
                        success = False
                        errors.append(str(e)[:200])

                # Update affordances from surface
                trace.affordances = await surface.list_affordances()

                # Record step
                step = StepRecord(
                    step_number=step_num,
                    thought_summary=decision.thought_summary,
                    action=decision.action,
                    action_type=decision.action_type,
                    result=result[:500],
                    success=success,
                    extracted_facts=decision.extracted_facts,
                    affordances_discovered=decision.extracted_facts,
                    errors=errors,
                    tokens_used=decision.tokens_used,
                    latency_ms=step_latency,
                    metadata={"uncertainty": decision.uncertainty},
                )
                trace.add_step(step)

                # Update history for agent context
                history.append(
                    {
                        "step": step_num,
                        "thought_summary": decision.thought_summary,
                        "action": decision.action,
                        "action_type": decision.action_type,
                        "result": result[:200],
                        "success": success,
                    }
                )

                self.callback.on_step_complete(step, trace)

                if decision.done:
                    reason = decision.done_reason or ""
                    trace.complete(
                        success="success" in reason.lower()
                        or "complete" in reason.lower()
                        or decision.uncertainty < 0.3,
                        failure_reason=reason if not success else None,
                    )
                    break
            else:
                trace.complete(
                    success=False,
                    failure_reason=f"Max steps ({max_steps}) reached",
                )

        except Exception as e:
            logger.error(f"Run failed: {e}")
            trace.complete(success=False, failure_reason=str(e))
            self.callback.on_error(str(e), trace)

        finally:
            with contextlib.suppress(Exception):
                await surface.teardown()
            with contextlib.suppress(Exception):
                await backend.close()

        # Score and analyze
        trace.scores = self.scoring.score(trace)
        analysis = self.pipeline.analyze(trace)

        self.callback.on_run_complete(trace, analysis)
        return trace, analysis


def create_surface(surface_type: SurfaceType, target: str, config: AgentUXConfig) -> Surface:
    """Factory function to create the appropriate surface adapter."""
    # In demo mode, use MockSurface to avoid needing real browsers/servers
    if config.demo_mode:
        from agentux.surfaces.mock import MockSurface

        return MockSurface(surface_type, target)

    from agentux.surfaces.browser import BrowserSurface
    from agentux.surfaces.cli_surface import CLISurface
    from agentux.surfaces.markdown import MarkdownSurface
    from agentux.surfaces.mcp import MCPSurface

    if surface_type == SurfaceType.BROWSER:
        return BrowserSurface(target, config.browser)
    elif surface_type == SurfaceType.MARKDOWN:
        return MarkdownSurface(target)
    elif surface_type == SurfaceType.CLI:
        return CLISurface(target, config.cli)
    elif surface_type == SurfaceType.MCP:
        return MCPSurface(target, config.mcp)
    else:
        raise ValueError(f"Unknown surface type: {surface_type}")


def create_backend(name: str, config: AgentUXConfig) -> AgentBackend:
    """Factory function to create the appropriate agent backend."""
    from agentux.agents.anthropic_backend import AnthropicBackend
    from agentux.agents.mock import MockBackend
    from agentux.agents.openai_backend import OpenAIBackend

    if name == "mock" or config.demo_mode:
        return MockBackend()
    elif name == "anthropic":
        return AnthropicBackend(config.backend)
    elif name in ("openai", ""):
        return OpenAIBackend(config.backend)
    else:
        # Try OpenAI-compatible
        return OpenAIBackend(config.backend)
