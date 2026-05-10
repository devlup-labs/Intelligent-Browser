"""
Observe node — read the current page state via DOM extraction.

Takes a screenshot only when:
  - Very few interactive elements found (< 3)
  - The agent is stuck (same action failed twice)
"""

from playwright.async_api import Page

from intellibrowse.agent.state import AgentState
from intellibrowse.browser.observation import get_page_state, take_screenshot
from intellibrowse.memory.longterm import get_domain_hints
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


async def observe(state: AgentState, page: Page) -> dict:
    """
    Observe the current page. Returns partial state update.
    """
    step = state.get("current_step", 0)
    logger.info("[step %d] observing page...", step)

    # Wait briefly for any pending navigation/DOM updates to settle
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=3000)
    except Exception:
        pass  # Timeout is fine — page might already be loaded

    # Small delay for JS-heavy pages (React, GitHub, etc.)
    await page.wait_for_timeout(500)

    # Extract DOM state
    page_text, elements = await get_page_state(page)
    page_url = page.url

    # If first attempt returns 0 elements, retry after a longer wait
    if len(elements) == 0:
        logger.info("[step %d] no elements found — waiting and retrying...", step)
        await page.wait_for_timeout(1500)
        page_text, elements = await get_page_state(page)

    update: dict = {
        "page_state": page_text,
        "page_url": page_url,
    }

    # Get domain hints from long-term memory
    domain_hints = get_domain_hints(page_url)
    if domain_hints:
        update["domain_hints"] = domain_hints

    # Take screenshot if stuck or tree is too sparse
    needs_screenshot = (
        len(elements) < 3  # Nearly empty page
        or state.get("consecutive_failures", 0) >= 2  # Stuck
    )

    if needs_screenshot:
        logger.info("[step %d] taking screenshot (sparse tree or stuck)", step)
        b64 = await take_screenshot(page)
        if b64:
            update["screenshot_b64"] = b64
    else:
        # Clear any old screenshot
        update["screenshot_b64"] = ""

    return update
