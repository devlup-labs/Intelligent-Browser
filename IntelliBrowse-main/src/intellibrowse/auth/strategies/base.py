from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
import random
from playwright.async_api import Page


class LoginStrategy(ABC):
    """
    Each subclass knows the CSS selectors and flow for one platform.
    Implementations must NEVER log or raise the password in error messages.
    """

    async def _human_warmup(self, page: Page) -> None:
        """
        Simulate a human arriving on a page before interacting with any form.
        Pause briefly and move the mouse to a neutral position.
        Called at the start of every login() implementation.
        """
        await asyncio.sleep(random.uniform(0.8, 2.2))
        await page.mouse.move(
            random.randint(300, 700),
            random.randint(200, 400),
        )
        await asyncio.sleep(random.uniform(0.3, 0.7))

    @abstractmethod
    async def login(self, page: Page, username: str, password: str) -> None:
        """
        Navigate to the login page and complete authentication.
        Raises LoginFailedError on failure.
        """
        ...


class LoginFailedError(Exception):
    """Raised when login could not be completed. Message must not contain credentials."""


class MFARequiredError(Exception):
    """
    Raised when MFA/2FA is required and human input is needed.
    Carry a `platform` attribute so the caller can prompt the user.
    """

    def __init__(self, platform: str, prompt: str = "Enter your verification code"):
        super().__init__(prompt)
        self.platform = platform
        self.prompt = prompt
