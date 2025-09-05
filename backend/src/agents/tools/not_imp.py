from crewai.tools import BaseTool
from pydantic import BaseModel, Field, ConfigDict
from typing import Type, Optional
from playwright.async_api import Page


class SmartLoginInput(BaseModel):
    url: str = Field(..., description="URL of the site to login to")
    parsed_html: str = Field(..., description="Parsed HTML content of the login page")


class SmartLoginTool(BaseTool):
    name: str = "smart_login_tool"
    description: str = (
        "Hardcoded tool that logs into Instagram using username & password. "
        "Takes parsed_html and page as inputs for CrewAI compatibility."
    )
    args_schema: Type[SmartLoginInput] = SmartLoginInput

    async def _arun(
        self,
        parsed_html: Optional[str] = None,
        page: Optional[Page] = None
    ) -> dict:
        """Async login to Instagram (hardcoded username + password).
        Uses the provided Playwright page and does not close it afterwards.
        """
        try:
            if page is None:
                return {"success": False, "message": "No Playwright page object provided"}

            username = "Intelli_Browse"
            password = "wiggly.213"

            # Assume page is already created by CrewAI caller
            await page.goto("https://www.instagram.com/accounts/login/")
            await page.wait_for_selector('input[name="username"]', timeout=1500)
            await page.fill('input[name="username"]', username)
            await page.fill('input[name="password"]', password)
            await page.click('button[type="submit"]')

            # ✅ Do NOT close the page; just leave it for further steps
            return {
                "success": True,
                "message": "Login attempt made with hardcoded credentials. Page left open."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run(
        self,
        parsed_html: Optional[str] = None,
        page: Optional[Page] = None
    ) -> dict:
        raise NotImplementedError("Only async execution is supported for this tool")
