"""Tests for surface adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentux.core.models import AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface
from agentux.surfaces.markdown import MarkdownSurface

# ── Surface base interface ──────────────────────────────────────────────────


class TestSurfaceBaseInterface:
    """Verify that Surface is a proper abstract base class."""

    def test_cannot_instantiate(self) -> None:
        with pytest.raises(TypeError):
            Surface()  # type: ignore[abstract]

    def test_subclass_must_implement_methods(self) -> None:
        """A subclass missing abstract methods cannot be instantiated."""

        class IncompleteSurface(Surface):
            surface_type = SurfaceType.BROWSER

        with pytest.raises(TypeError):
            IncompleteSurface()  # type: ignore[abstract]


# ── MarkdownSurface ─────────────────────────────────────────────────────────


class TestMarkdownSurface:
    @pytest.fixture
    def md_file(self, sample_markdown_content: str, tmp_path: Path) -> Path:
        p = tmp_path / "test.md"
        p.write_text(sample_markdown_content)
        return p

    @pytest.fixture
    async def surface(self, md_file: Path) -> MarkdownSurface:
        s = MarkdownSurface(str(md_file))
        await s.setup()
        return s

    async def test_setup_parses_sections(self, surface: MarkdownSurface) -> None:
        assert len(surface._sections) > 0

    async def test_surface_type(self, surface: MarkdownSurface) -> None:
        assert surface.surface_type == SurfaceType.MARKDOWN

    async def test_discover_returns_affordances(self, surface: MarkdownSurface) -> None:
        affordances = await surface.discover()
        assert len(affordances) > 0
        section_affs = [a for a in affordances if a.kind == "section"]
        assert len(section_affs) >= 3  # Getting Started, Installation, Configuration, Usage, FAQ

    async def test_discover_finds_links(self, surface: MarkdownSurface) -> None:
        affordances = await surface.discover()
        link_affs = [a for a in affordances if a.kind == "link"]
        assert len(link_affs) >= 1  # "the docs" link

    async def test_discover_finds_code_blocks(self, surface: MarkdownSurface) -> None:
        affordances = await surface.discover()
        code_affs = [a for a in affordances if a.kind == "code_block"]
        assert len(code_affs) >= 1

    async def test_observe_shows_toc(self, surface: MarkdownSurface) -> None:
        obs = await surface.observe()
        assert "Markdown document" in obs
        assert "Getting Started" in obs

    async def test_act_read_section(self, surface: MarkdownSurface) -> None:
        result = await surface.act("read_section", {"title": "Installation"})
        assert "Installation" in result or "pip install" in result

    async def test_act_read_section_not_found(self, surface: MarkdownSurface) -> None:
        result = await surface.act("read_section", {"title": "Nonexistent"})
        assert "not found" in result.lower()

    async def test_act_search(self, surface: MarkdownSurface) -> None:
        result = await surface.act("search", {"query": "API_KEY"})
        assert "API_KEY" in result or "Configuration" in result

    async def test_act_search_no_results(self, surface: MarkdownSurface) -> None:
        result = await surface.act("search", {"query": "zzz_nonexistent_zzz"})
        assert "No results" in result

    async def test_act_list_sections(self, surface: MarkdownSurface) -> None:
        result = await surface.act("list_sections")
        assert "Getting Started" in result

    async def test_act_read_all(self, surface: MarkdownSurface) -> None:
        result = await surface.act("read_all")
        assert len(result) > 0

    async def test_act_read_range(self, surface: MarkdownSurface) -> None:
        result = await surface.act("read_range", {"start": 0, "length": 50})
        assert len(result) == 50

    async def test_act_unknown_action(self, surface: MarkdownSurface) -> None:
        result = await surface.act("fly_to_moon")
        assert "Unknown action" in result

    async def test_summarize_state(self, surface: MarkdownSurface) -> None:
        state = await surface.summarize_state()
        assert state["surface_type"] == "markdown"
        assert state["total_sections"] > 0
        assert "coverage_pct" in state

    async def test_read_section_updates_affordance_status(self, surface: MarkdownSurface) -> None:
        await surface.discover()
        await surface.act("read_section", {"title": "Installation"})
        affordances = await surface.list_affordances()
        installation = [a for a in affordances if "Installation" in a.name]
        if installation:
            assert installation[0].status == AffordanceStatus.INTERACTED

    async def test_context_manager(self, md_file: Path) -> None:
        async with MarkdownSurface(str(md_file)) as s:
            obs = await s.observe()
            assert "Markdown document" in obs

    async def test_setup_file_not_found(self) -> None:
        s = MarkdownSurface("/nonexistent/path.md")
        with pytest.raises(FileNotFoundError):
            await s.setup()

    async def test_teardown_is_noop(self, surface: MarkdownSurface) -> None:
        """Teardown should complete without error."""
        await surface.teardown()


# ── CLISurface basics ───────────────────────────────────────────────────────


class TestCLISurfaceBasics:
    """Test CLISurface construction and attribute checks (no subprocess calls)."""

    def test_surface_type(self) -> None:
        from agentux.surfaces.cli_surface import CLISurface

        s = CLISurface("echo")
        assert s.surface_type == SurfaceType.CLI

    def test_target_stored(self) -> None:
        from agentux.surfaces.cli_surface import CLISurface

        s = CLISurface("ls")
        assert s.target == "ls"

    async def test_setup_with_real_binary(self) -> None:
        """echo is universally available; setup should succeed."""
        from agentux.surfaces.cli_surface import CLISurface

        s = CLISurface("echo")
        await s.setup()
        await s.teardown()

    async def test_setup_with_missing_binary(self) -> None:
        from agentux.core.exceptions import CLISurfaceError
        from agentux.surfaces.cli_surface import CLISurface

        s = CLISurface("nonexistent_binary_xyz_12345")
        with pytest.raises(CLISurfaceError):
            await s.setup()
