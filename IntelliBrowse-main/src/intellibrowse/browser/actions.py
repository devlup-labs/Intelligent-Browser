"""
Browser actions — execute atomic actions on the page.

Each function takes a Page and parameters, executes ONE action, returns a result string.
Element resolution uses JavaScript to re-query interactive elements by index,
matching the same selector used in observation.py.
"""

import os
import time

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)

# Default timeout for element interactions (ms)
ACTION_TIMEOUT = 5000

# Screenshot save directory
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "screenshots")

# Same selectors as observation.py — must stay in sync
_INTERACTIVE_SELECTORS = (
    'a[href], button, input, select, textarea, '
    '[role="link"], [role="button"], [role="checkbox"], '
    '[role="radio"], [role="tab"], [role="menuitem"], '
    '[role="combobox"], [role="searchbox"], [role="switch"], '
    '[role="slider"], [role="option"], [role="treeitem"], '
    '[contenteditable="true"]'
)

# JavaScript that returns the nth visible interactive element info
_GET_ELEMENT_JS = """
(index) => {
    const selectors = '__SELECTORS__';
    const all = document.querySelectorAll(selectors);
    const visible = Array.from(all).filter(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') return false;
        if (style.opacity === '0') return false;
        return true;
    });
    if (index < 0 || index >= visible.length) return null;
    const el = visible[index];
    const tag = el.tagName.toLowerCase();
    let role = el.getAttribute('role') || '';
    if (!role) {
        if (tag === 'a') role = 'link';
        else if (tag === 'button' || el.type === 'submit') role = 'button';
        else if (tag === 'input') role = el.type || 'textbox';
        else if (tag === 'select') role = 'combobox';
        else if (tag === 'textarea') role = 'textbox';
        else role = tag;
    }
    let name = el.getAttribute('aria-label') || el.getAttribute('title')
        || el.getAttribute('placeholder') || el.innerText?.trim().substring(0, 80) || '';
    return { tag, role, name, index };
}
""".replace('__SELECTORS__', _INTERACTIVE_SELECTORS)

# JavaScript to get element position and info for native clicking
_GET_CLICK_TARGET_JS = """
(index) => {
    const selectors = '__SELECTORS__';
    const all = document.querySelectorAll(selectors);
    const visible = Array.from(all).filter(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    });
    if (index < 0 || index >= visible.length) return { ok: false, error: `index ${index} out of range (0-${visible.length - 1})` };
    const el = visible[index];
    el.scrollIntoView({ block: 'center' });
    const rect = el.getBoundingClientRect();
    const tag = el.tagName.toLowerCase();
    const name = el.getAttribute('aria-label') || el.innerText?.trim().substring(0, 60) || '';
    const role = el.getAttribute('role') || tag;
    return {
        ok: true, role, name,
        x: rect.x + rect.width / 2,
        y: rect.y + rect.height / 2
    };
}
""".replace('__SELECTORS__', _INTERACTIVE_SELECTORS)

# JavaScript to focus and clear the nth visible interactive element (for real typing)
_FOCUS_AND_CLEAR_JS = """
(index) => {
    const selectors = '__SELECTORS__';
    const all = document.querySelectorAll(selectors);
    const visible = Array.from(all).filter(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) return false;
        const style = window.getComputedStyle(el);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    });
    if (index < 0 || index >= visible.length) return { ok: false, error: `index ${index} out of range (0-${visible.length - 1})` };
    const el = visible[index];
    el.scrollIntoView({ block: 'center' });
    el.focus();
    el.click();
    // Select all text and clear it
    if (el.select) el.select();
    el.value = '';
    el.dispatchEvent(new Event('input', { bubbles: true }));
    const name = el.getAttribute('aria-label') || el.getAttribute('placeholder') || '';
    return { ok: true, name };
}
""".replace('__SELECTORS__', _INTERACTIVE_SELECTORS)


async def click(page: Page, index: int) -> str:
    """
    Click an element using Playwright's native mouse click.

    Uses JS to find the element and get its position, then
    page.mouse.click() for a real browser click that works with
    all frameworks (React, Vue, Angular, etc.)
    """
    try:
        # Get element position via JS
        result = await page.evaluate(_GET_CLICK_TARGET_JS, index)
        if not result or not result.get("ok"):
            error = result.get("error", "unknown") if result else "element not found"
            return f"FAILED: {error}"

        # Small delay after scroll
        await page.wait_for_timeout(200)

        # Native Playwright mouse click at element center
        await page.mouse.click(result["x"], result["y"])

        # Wait for navigation/DOM changes
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=3000)
        except Exception:
            pass
        await page.wait_for_timeout(500)

        return f'Clicked {result["role"]} "{result["name"]}" — now at {page.url}'
    except Exception as e:
        return f"FAILED: click error: {e}"


async def type_text(page: Page, index: int, text: str) -> str:
    """
    Type text into an element using real keystrokes.

    Uses Playwright's keyboard.type() which simulates actual key presses.
    This triggers autocomplete dropdowns, search suggestions, and other
    JavaScript-driven UI that listens for keydown/keyup events.
    """
    try:
        # Focus and clear the element via JS
        result = await page.evaluate(_FOCUS_AND_CLEAR_JS, index)
        if not result or not result.get("ok"):
            error = result.get("error", "unknown") if result else "element not found"
            return f"FAILED: {error}"

        # Type with real keystrokes — this triggers autocomplete/dropdown
        await page.keyboard.type(text, delay=50)

        # Wait for autocomplete/dropdown to appear
        await page.wait_for_timeout(800)

        return f'Typed "{text}" into "{result["name"]}" (dropdown may have appeared — check page state)'
    except Exception as e:
        return f"FAILED: type error: {e}"


async def press_key(page: Page, index: int, key: str) -> str:
    """Press a key (Enter, Tab, Escape, etc.) on the currently focused element."""
    try:
        # Just press the key — it goes to whatever element currently has focus
        await page.keyboard.press(key)
        await page.wait_for_timeout(500)
        return f'Pressed "{key}" — now at {page.url}'
    except Exception as e:
        return f"FAILED: key press error: {e}"


async def navigate(page: Page, url: str) -> str:
    """Navigate to a URL."""
    try:
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        return f'Navigated to {page.url} — title: "{title}"'
    except PlaywrightTimeout:
        return f"FAILED: navigation to {url} timed out"
    except Exception as e:
        return f"FAILED: navigation error: {e}"


async def scroll(page: Page, direction: str) -> str:
    """Scroll the page up or down."""
    try:
        pixels = 500 if direction == "down" else -500
        await page.mouse.wheel(0, pixels)
        await page.wait_for_timeout(300)
        return f"Scrolled {direction}"
    except Exception as e:
        return f"FAILED: scroll error: {e}"


async def go_back(page: Page) -> str:
    """Go back to the previous page."""
    try:
        await page.go_back(wait_until="domcontentloaded", timeout=10000)
        title = await page.title()
        return f'Went back — now at {page.url} ("{title}")'
    except Exception as e:
        return f"FAILED: go_back error: {e}"


async def select_option(page: Page, index: int, value: str) -> str:
    """Select an option from a dropdown by index."""
    try:
        info = await page.evaluate(_GET_ELEMENT_JS, index)
        if not info:
            return f"FAILED: element [{index}] not found"
        result = await page.evaluate(f"""
            (args) => {{
                const selectors = '{_INTERACTIVE_SELECTORS}';
                const all = document.querySelectorAll(selectors);
                const visible = Array.from(all).filter(el => el.offsetParent !== null);
                const el = visible[args.index];
                if (!el || el.tagName.toLowerCase() !== 'select') return {{ ok: false, error: 'not a select element' }};
                el.value = args.value;
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return {{ ok: true }};
            }}
        """, {"index": index, "value": value})
        if result and result.get("ok"):
            return f'Selected "{value}" in {info["role"]} "{info["name"]}"'
        return f'FAILED: {result.get("error", "unknown")}'
    except Exception as e:
        return f"FAILED: select error: {e}"


async def take_screenshot_action(page: Page) -> str:
    """Take a screenshot and save it to the screenshots directory."""
    try:
        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        title = (await page.title()).replace(" ", "_")[:30]
        filename = f"{timestamp}_{title}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)

        await page.screenshot(path=filepath, full_page=False)
        logger.info("screenshot saved: %s", filepath)
        return f'Screenshot saved to {filepath}'
    except Exception as e:
        return f"FAILED: screenshot error: {e}"


async def wait_for_page(page: Page, seconds: float = 2.0) -> str:
    """Wait for the page to settle."""
    try:
        await page.wait_for_timeout(int(seconds * 1000))
        return f"Waited {seconds}s for page to settle"
    except Exception as e:
        return f"FAILED: wait error: {e}"


# ── Action dispatcher ─────────────────────────────────────────────────

ACTION_MAP = {
    "click": click,
    "type": type_text,
    "press_key": press_key,
    "navigate": navigate,
    "scroll": scroll,
    "go_back": go_back,
    "select_option": select_option,
    "screenshot": take_screenshot_action,
    "wait": wait_for_page,
}


async def execute_action(page: Page, action: str, **kwargs) -> str:
    """
    Dispatch an action by name with kwargs.
    This is the single entry point used by the Act node.
    """
    handler = ACTION_MAP.get(action)
    if handler is None:
        return f'FAILED: unknown action "{action}". Available: {list(ACTION_MAP.keys())}'

    logger.info("executing: %s(%s)", action, kwargs)
    result = await handler(page, **kwargs)
    logger.info("result: %s", result[:200])
    return result
