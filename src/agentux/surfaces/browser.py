"""Browser surface adapter using Playwright."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urljoin

from agentux.core.config import BrowserConfig
from agentux.core.exceptions import BrowserSurfaceError
from agentux.core.models import Affordance, AffordanceStatus, SurfaceType
from agentux.surfaces.base import Surface

logger = logging.getLogger(__name__)

SEMANTIC_SECTIONS = [
    ("header", "header, [role=banner]"),
    ("navigation", "nav, [role=navigation]"),
    ("hero", ".hero, [class*=hero], section:first-of-type"),
    ("features", "[class*=feature], [id*=feature]"),
    ("pricing", "[class*=pricing], [id*=pricing], [href*=pricing]"),
    ("docs", "[class*=doc], [id*=doc], [href*=doc]"),
    ("quickstart", "[class*=quickstart], [class*=getting-started], [id*=quickstart]"),
    ("forms", "form"),
    ("cta", "[class*=cta], button[class*=primary], a[class*=primary]"),
    ("footer", "footer, [role=contentinfo]"),
    ("search", "[type=search], [class*=search], [role=search]"),
    ("login", "[class*=login], [href*=login], [class*=signin]"),
    ("signup", "[class*=signup], [href*=signup], [class*=register]"),
]


class BrowserSurface(Surface):
    """Surface adapter for web pages using Playwright browser automation."""

    surface_type = SurfaceType.BROWSER

    def __init__(self, target: str, config: BrowserConfig | None = None) -> None:
        self.target = target
        self.config = config or BrowserConfig()
        self._browser: Any = None
        self._page: Any = None
        self._playwright: Any = None
        self._affordances: list[Affordance] = []
        self._navigation_history: list[str] = []
        self._current_url: str = target

    async def setup(self) -> None:
        try:
            from playwright.async_api import async_playwright

            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=self.config.headless)
            self._page = await self._browser.new_page(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            )
            self._page.set_default_timeout(self.config.timeout_ms)
            await self._page.goto(self.target, wait_until="domcontentloaded")
            self._current_url = self._page.url
            self._navigation_history.append(self._current_url)
        except ImportError:
            raise BrowserSurfaceError(
                "Playwright not installed. Run: playwright install chromium"
            ) from None
        except Exception as e:
            raise BrowserSurfaceError(f"Failed to initialize browser: {e}") from e

    async def teardown(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def discover(self) -> list[Affordance]:
        if not self._page:
            raise BrowserSurfaceError("Browser not initialized")

        self._affordances = []
        for name, selector in SEMANTIC_SECTIONS:
            try:
                elements = await self._page.query_selector_all(selector)
                if elements:
                    self._affordances.append(
                        Affordance(
                            name=name,
                            kind="section",
                            status=AffordanceStatus.DISCOVERED,
                            relevant=True,
                            metadata={"selector": selector, "count": len(elements)},
                        )
                    )
            except Exception:
                pass

        # Discover links
        try:
            links = await self._page.evaluate("""
                () => Array.from(document.querySelectorAll('a[href]'))
                    .map(a => ({text: a.textContent?.trim()?.substring(0, 80), href: a.href}))
                    .filter(l => l.text && l.text.length > 0)
                    .slice(0, 50)
            """)
            for link in links:
                self._affordances.append(
                    Affordance(
                        name=link.get("text", "")[:60],
                        kind="link",
                        status=AffordanceStatus.DISCOVERED,
                        relevant=True,
                        metadata={"href": link.get("href", "")},
                    )
                )
        except Exception:
            pass

        return self._affordances

    async def act(self, action: str, params: dict[str, Any] | None = None) -> str:
        if not self._page:
            raise BrowserSurfaceError("Browser not initialized")

        params = params or {}
        try:
            if action == "click":
                selector = params.get("selector", "")
                text = params.get("text", "")
                if text:
                    await self._page.get_by_text(text, exact=False).first.click()
                elif selector:
                    await self._page.click(selector)
                else:
                    return "Error: click requires 'selector' or 'text' param"
                await self._page.wait_for_load_state("domcontentloaded")
                self._current_url = self._page.url
                self._navigation_history.append(self._current_url)
                return f"Clicked. Now at: {self._current_url}"

            elif action == "navigate":
                url = params.get("url", "")
                if not url.startswith("http"):
                    url = urljoin(self._current_url, url)
                await self._page.goto(url, wait_until="domcontentloaded")
                self._current_url = self._page.url
                self._navigation_history.append(self._current_url)
                return f"Navigated to: {self._current_url}"

            elif action == "type":
                selector = params.get("selector", "input")
                text = params.get("text", "")
                await self._page.fill(selector, text)
                return f"Typed '{text}' into {selector}"

            elif action == "scroll":
                direction = params.get("direction", "down")
                amount = params.get("amount", 500)
                if direction == "down":
                    await self._page.evaluate(f"window.scrollBy(0, {amount})")
                else:
                    await self._page.evaluate(f"window.scrollBy(0, -{amount})")
                return f"Scrolled {direction} by {amount}px"

            elif action == "back":
                await self._page.go_back()
                self._current_url = self._page.url
                return f"Went back. Now at: {self._current_url}"

            elif action == "screenshot":
                path = params.get("path", "screenshot.png")
                await self._page.screenshot(path=path, full_page=True)
                return f"Screenshot saved to {path}"

            elif action == "extract_text":
                selector = params.get("selector", "body")
                text = await self._page.inner_text(selector)
                return text[:2000]

            elif action == "wait":
                ms = params.get("ms", 1000)
                await asyncio.sleep(ms / 1000)
                return f"Waited {ms}ms"

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Error performing {action}: {e}"

    async def observe(self) -> str:
        if not self._page:
            raise BrowserSurfaceError("Browser not initialized")

        try:
            title = await self._page.title()
            url = self._page.url
            # Get visible text content (truncated)
            text = await self._page.evaluate("""
                () => {
                    const body = document.body;
                    if (!body) return '';
                    return body.innerText?.substring(0, 3000) || '';
                }
            """)
            meta_desc = await self._page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[name="description"]');
                    return meta ? meta.content : '';
                }
            """)

            parts = [
                f"URL: {url}",
                f"Title: {title}",
            ]
            if meta_desc:
                parts.append(f"Description: {meta_desc}")
            parts.append(f"\nVisible text:\n{text}")
            return "\n".join(parts)

        except Exception as e:
            return f"Error observing page: {e}"

    async def summarize_state(self) -> dict[str, Any]:
        return {
            "surface_type": self.surface_type.value,
            "current_url": self._current_url,
            "target": self.target,
            "pages_visited": len(self._navigation_history),
            "navigation_history": self._navigation_history[-10:],
            "affordances_found": len(self._affordances),
        }

    async def list_affordances(self) -> list[Affordance]:
        return self._affordances
