"""
Browser lifecycle manager — async context manager for Playwright Chromium.

Usage:
    async with BrowserManager() as bm:
        page = await bm.new_page()
        await page.goto("https://example.com")
"""

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from intellibrowse.config import settings
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


class BrowserManager:
    """Manages Playwright browser lifecycle with a single persistent context."""

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def start(self) -> "BrowserManager":
        """Launch browser and create a persistent context."""
        logger.info("launching chromium (headless=%s)", settings.headless)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=settings.headless)
        self._context = await self._browser.new_context(
            viewport={
                "width": settings.viewport_width,
                "height": settings.viewport_height,
            },
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        self._page = await self._context.new_page()
        logger.info("browser ready — viewport %dx%d", settings.viewport_width, settings.viewport_height)
        return self

    async def stop(self):
        """Gracefully close everything."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("browser closed")

    @property
    def page(self) -> Page:
        """Get the active page. Raises if browser not started."""
        if self._page is None:
            raise RuntimeError("browser not started — call start() first")
        return self._page

    async def new_page(self) -> Page:
        """Create a new page in the existing context."""
        if self._context is None:
            raise RuntimeError("browser not started — call start() first")
        self._page = await self._context.new_page()
        return self._page

    # Async context manager support
    async def __aenter__(self) -> "BrowserManager":
        return await self.start()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
