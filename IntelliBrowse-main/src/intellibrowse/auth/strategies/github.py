from __future__ import annotations
import asyncio
import random
from playwright.async_api import Page, TimeoutError as PWTimeout
from .base import LoginStrategy, LoginFailedError, MFARequiredError


class GitHubStrategy(LoginStrategy):
    LOGIN_URL = "https://github.com/login"

    async def login(self, page: Page, username: str, password: str) -> None:
        await page.goto(self.LOGIN_URL, wait_until="domcontentloaded")
        await self._human_warmup(page)
        try:
            username_el = page.locator("#login_field")
            await username_el.click()
            await username_el.type(username, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.4, 0.9))

            password_el = page.locator("#password")
            await password_el.click()
            await password_el.type(password, delay=random.uniform(70, 150))
            await asyncio.sleep(random.uniform(0.3, 0.6))

            await page.click('[name="commit"]', timeout=5_000)
        except PWTimeout as exc:
            raise LoginFailedError(f"GitHub login timed out: {exc}") from exc

        await asyncio.sleep(random.uniform(2.0, 3.0))
        url = page.url

        if "two-factor" in url or "sessions/two-factor" in url:
            raise MFARequiredError("github")
        if "login" in url:
            raise LoginFailedError("GitHub login failed - still on login page")
