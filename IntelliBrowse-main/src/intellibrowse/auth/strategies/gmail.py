from __future__ import annotations
import asyncio
import random
from playwright.async_api import Page, TimeoutError as PWTimeout
from .base import LoginStrategy, LoginFailedError, MFARequiredError


class GmailStrategy(LoginStrategy):
    LOGIN_URL = "https://accounts.google.com/signin/v2/identifier"

    async def login(self, page: Page, username: str, password: str) -> None:
        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
        await self._human_warmup(page)
        try:
            email_el = page.locator('input[type="email"]')
            await email_el.click()
            await email_el.type(username, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.4, 0.8))

            await page.click("#identifierNext", timeout=5_000)
            await page.wait_for_selector('input[type="password"]', timeout=10_000)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            password_el = page.locator('input[type="password"]')
            await password_el.click()
            await password_el.type(password, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.3, 0.6))

            await page.click("#passwordNext", timeout=5_000)
        except PWTimeout as exc:
            raise LoginFailedError(f"Gmail login timed out: {exc}") from exc

        await asyncio.sleep(random.uniform(2.5, 4.0))
        url = page.url

        if "challenge" in url or "signin/v2" in url:
            raise MFARequiredError("gmail")
        if "signin" in url:
            raise LoginFailedError("Gmail login did not complete successfully")
