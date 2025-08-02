from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playwright.async_api import Page, PlaywrightError

class GoToPageSchema(BaseModel):
    url: str = Field(..., description="The full URL to navigate to (e.g., https://www.google.com).")

class GoToPageTool(BaseTool):
    name: str 
    description: str
    args_schema: type[BaseModel] = GoToPageSchema
    page: Page

    async def _run(self, url: str) -> str:
        try:
            await self.page.goto(url, wait_until='load')
            return f"Successfully navigated to {url}. The page content is now available."
        except PlaywrightError as e:
           return f"Navigation failed due to browser error: {e}"
        except TimeoutError as e:
           return f"Navigation to {url} timed out: {e}"