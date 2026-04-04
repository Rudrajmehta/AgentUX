"""Markdown surface adapter for plain-text/markdown content evaluation."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from markdown_it import MarkdownIt

from agentux.core.models import Affordance, AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface

logger = logging.getLogger(__name__)


class MarkdownSurface(Surface):
    """Surface adapter for markdown documents and llms.txt files."""

    surface_type = SurfaceType.MARKDOWN

    def __init__(self, target: str) -> None:
        self.target = target
        self._content: str = ""
        self._sections: list[dict[str, Any]] = []
        self._affordances: list[Affordance] = []
        self._read_sections: set[str] = set()
        self._current_position: int = 0

    async def setup(self) -> None:
        if self.target.startswith(("http://", "https://")):
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(self.target)
                resp.raise_for_status()
                self._content = resp.text
        else:
            from pathlib import Path

            path = Path(self.target)
            if path.exists():
                self._content = path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(f"Markdown file not found: {self.target}")

        self._parse_structure()

    async def teardown(self) -> None:
        pass

    def _parse_structure(self) -> None:
        """Parse markdown into sections based on headings."""
        md = MarkdownIt()
        tokens = md.parse(self._content)

        current_section: dict[str, Any] = {
            "title": "(preamble)",
            "level": 0,
            "content": "",
            "start_line": 0,
        }
        self._sections = []

        for token in tokens:
            if token.type == "heading_open":
                if current_section["content"].strip():
                    self._sections.append(current_section)
                level = int(token.tag[1])  # h1 -> 1, h2 -> 2, etc.
                current_section = {
                    "title": "",
                    "level": level,
                    "content": "",
                    "start_line": token.map[0] if token.map else 0,
                }
            elif token.type == "inline" and not current_section["title"]:
                current_section["title"] = token.content
            elif token.type in ("inline", "fence", "code_block", "html_block"):
                current_section["content"] += token.content + "\n"

        if current_section["content"].strip() or current_section["title"]:
            self._sections.append(current_section)

    async def discover(self) -> list[Affordance]:
        self._affordances = []
        for section in self._sections:
            title = section["title"] or "(untitled)"
            self._affordances.append(
                Affordance(
                    name=title,
                    kind="section",
                    status=AffordanceStatus.DISCOVERED,
                    relevant=True,
                    metadata={
                        "level": section["level"],
                        "content_length": len(section["content"]),
                        "start_line": section["start_line"],
                    },
                )
            )

        # Discover links in content
        import re

        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(self._content):
            self._affordances.append(
                Affordance(
                    name=match.group(1)[:60],
                    kind="link",
                    status=AffordanceStatus.DISCOVERED,
                    relevant=True,
                    metadata={"href": match.group(2)},
                )
            )

        # Discover code blocks
        code_block_pattern = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
        for i, match in enumerate(code_block_pattern.finditer(self._content)):
            lang = match.group(1) or "text"
            self._affordances.append(
                Affordance(
                    name=f"code_block_{i}_{lang}",
                    kind="code_block",
                    status=AffordanceStatus.DISCOVERED,
                    relevant=True,
                    metadata={"language": lang, "length": len(match.group(2))},
                )
            )

        return self._affordances

    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        params = params or {}

        if action == "read_section":
            title = params.get("title", "")
            for section in self._sections:
                if title.lower() in section["title"].lower():
                    self._read_sections.add(section["title"])
                    # Update affordance status
                    for aff in self._affordances:
                        if aff.name == section["title"]:
                            aff.status = AffordanceStatus.INTERACTED
                    content = section["content"][:2000]
                    return f"## {section['title']}\n{content}"
            return f"Section '{title}' not found."

        elif action == "search":
            query = params.get("query", "").lower()
            results = []
            for section in self._sections:
                full = f"{section['title']} {section['content']}".lower()
                if query in full:
                    self._read_sections.add(section["title"])
                    snippet = section["content"][:300]
                    results.append(f"## {section['title']}\n{snippet}...")
            if results:
                return "\n\n".join(results[:5])
            return f"No results found for '{query}'"

        elif action == "read_all":
            self._read_sections = {s["title"] for s in self._sections}
            return self._content[:4000]

        elif action == "list_sections":
            return "\n".join(
                f"{'  ' * s['level']}- {s['title']} ({len(s['content'])} chars)"
                for s in self._sections
            )

        elif action == "read_range":
            start = params.get("start", 0)
            length = params.get("length", 1000)
            chunk = self._content[start : start + length]
            self._current_position = start + length
            return chunk

        else:
            return f"Unknown action: {action}"

    async def observe(self) -> str:
        toc = "\n".join(
            f"{'  ' * s['level']}- {s['title']}"
            for s in self._sections
        )
        return (
            f"Markdown document: {self.target}\n"
            f"Total length: {len(self._content)} chars\n"
            f"Sections: {len(self._sections)}\n\n"
            f"Table of contents:\n{toc}"
        )

    async def summarize_state(self) -> dict[str, Any]:
        total = len(self._sections)
        read = len(self._read_sections)
        return {
            "surface_type": self.surface_type.value,
            "target": self.target,
            "total_sections": total,
            "sections_read": read,
            "coverage_pct": (read / total * 100) if total > 0 else 0,
            "total_chars": len(self._content),
            "sections_read_names": list(self._read_sections),
        }

    async def list_affordances(self) -> list[Affordance]:
        return self._affordances
