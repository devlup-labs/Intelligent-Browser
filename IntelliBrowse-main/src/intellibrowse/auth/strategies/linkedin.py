from __future__ import annotations
import asyncio
import random
from playwright.async_api import Page, TimeoutError as PWTimeout
from .base import LoginStrategy, LoginFailedError, MFARequiredError


class LinkedInStrategy(LoginStrategy):
    LOGIN_URL = "https://www.linkedin.com/login"

    async def login(self, page: Page, username: str, password: str) -> None:
        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
        await self._human_warmup(page)
        try:
            username_el = page.locator("#username")
            await username_el.click()
            await username_el.type(username, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.4, 0.9))

            password_el = page.locator("#password")
            await password_el.click()
            await password_el.type(password, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.3, 0.6))

            await page.click('[data-litms-control-urn="login-submit"]', timeout=5_000)
        except PWTimeout as exc:
            raise LoginFailedError(f"LinkedIn login timed out: {exc}") from exc

        await asyncio.sleep(random.uniform(2.0, 3.5))
        url = page.url

        if "checkpoint" in url or "challenge" in url:
            raise MFARequiredError("linkedin")
        if "feed" not in url and "mynetwork" not in url and "jobs" not in url:
            raise LoginFailedError("LinkedIn login did not reach expected page after submit")
