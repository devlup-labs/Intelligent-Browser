from playwright.async_api import async_playwright, Page, Browser

class BrowserManager:
    
    def __init__(self):
        self.p = None
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def start(self) -> Page:
        self.p = await async_playwright().start()
        self.browser = await self.p.chromium.launch(headless=False)
        self.page = await self.browser.new_page()
        return self.page

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.p:
            await self.p.stop()
        print("Browser session closed.")