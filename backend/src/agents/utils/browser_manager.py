import asyncio
import platform
from playwright.async_api import async_playwright, Page, Browser
import traceback

class BrowserManager:
    
    def __init__(self):
        self.p = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start(self) -> Page:
        try:
            # Set the correct event loop policy for Windows
            if platform.system() == "Windows":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
            self.p = await async_playwright().start()
            self.browser = await self.p.chromium.launch(headless=False)
            self.page = await self.browser.new_page()
        except Exception as e:
            traceback.print_exc()  # This prints the real error to console
            await self.close()
            raise RuntimeError(f"Failed to start browser session {e}") from e
        return self.page

    async def close(self):
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.p:
            await self.p.stop()
            self.p = None
        self.page = None
        print("Browser session closed.")