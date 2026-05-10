"""
Page observation — extract interactive elements and page structure for the LLM.

Uses JavaScript DOM queries to enumerate all visible interactive elements.
This replaces the deprecated `page.accessibility.snapshot()` which was removed
in Playwright 1.49+.

Each interactive element gets a numeric index so the agent can say "click [7]".
Elements are grouped by page section (nav, main, footer) to help the LLM
distinguish site navigation from actual page content.
"""

import base64
from playwright.async_api import Page

from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)

# JavaScript to extract all visible interactive elements + page context
_EXTRACT_JS = """
() => {
    // Gather interactive elements — MUST use same method as actions.py
    // querySelectorAll with comma-separated selectors returns DOM order, no duplicates
    const selectorStr = 'a[href], button, input, select, textarea, ' +
        '[role="link"], [role="button"], [role="checkbox"], ' +
        '[role="radio"], [role="tab"], [role="menuitem"], ' +
        '[role="combobox"], [role="searchbox"], [role="switch"], ' +
        '[role="slider"], [role="option"], [role="treeitem"], ' +
        '[contenteditable="true"]';
    const allElements = document.querySelectorAll(selectorStr);

    // Determine which section an element belongs to
    function getSection(el) {
        let node = el;
        while (node && node !== document.body) {
            const tag = node.tagName?.toLowerCase() || '';
            const role = node.getAttribute?.('role') || '';

            if (tag === 'nav' || role === 'navigation') return 'NAV';
            if (tag === 'header' || role === 'banner') return 'HEADER';
            if (tag === 'footer' || role === 'contentinfo') return 'FOOTER';
            if (tag === 'main' || role === 'main') return 'MAIN';
            if (tag === 'aside' || role === 'complementary') return 'SIDEBAR';
            if (role === 'dialog' || role === 'alertdialog') return 'DIALOG';

            node = node.parentElement;
        }
        return 'MAIN';
    }

    const interactive = Array.from(allElements)
        .filter(el => {
            // Must be visible
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return false;
            if (style.opacity === '0') return false;
            return true;
        })
        .map((el, i) => {
            const rect = el.getBoundingClientRect();
            const tag = el.tagName.toLowerCase();

            // Determine role
            let role = el.getAttribute('role') || '';
            if (!role) {
                if (tag === 'a') role = 'link';
                else if (tag === 'button' || el.type === 'submit') role = 'button';
                else if (tag === 'input') role = el.type || 'textbox';
                else if (tag === 'select') role = 'combobox';
                else if (tag === 'textarea') role = 'textbox';
                else role = tag;
            }

            // Determine name/label
            let name = el.getAttribute('aria-label')
                || el.getAttribute('title')
                || el.getAttribute('placeholder')
                || el.getAttribute('alt')
                || '';
            if (!name) {
                // Use visible text, but truncate and clean
                name = el.innerText?.trim().split('\\n')[0]?.substring(0, 80) || '';
            }
            if (!name && tag === 'input') {
                // Try associated label
                const id = el.getAttribute('id');
                if (id) {
                    const label = document.querySelector(`label[for="${id}"]`);
                    if (label) name = label.innerText?.trim().substring(0, 80) || '';
                }
            }

            return {
                tag,
                role,
                name: name.replace(/\\n/g, ' ').replace(/\\s+/g, ' ').trim(),
                type: el.getAttribute('type') || '',
                href: tag === 'a' ? (el.getAttribute('href') || '').substring(0, 120) : '',
                value: el.value || '',
                checked: el.checked || false,
                disabled: el.disabled || false,
                focused: document.activeElement === el,
                section: getSection(el),
            };
        });

    // Gather page headings for context
    const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
            level: parseInt(el.tagName[1]),
            text: el.innerText?.trim().substring(0, 120) || ''
        }))
        .filter(h => h.text);

    // Get some visible text for page context
    const mainEl = document.querySelector('main') || document.body;
    let visibleText = '';
    try { visibleText = (mainEl.innerText || '').substring(0, 300).trim(); } catch(e) {}

    return { interactive, headings, visibleText };
}
"""


async def get_page_state(page: Page) -> tuple[str, list[dict]]:
    """
    Extract page state via JavaScript DOM queries.

    Returns:
        (formatted_text, elements_list) — text goes into the prompt,
        elements list is used by actions to map index → element.
    """
    try:
        data = await page.evaluate(_EXTRACT_JS)
    except Exception as e:
        logger.warning("DOM extraction failed: %s", e)
        return f"URL: {page.url}\nTitle: (failed to read)\n[page extraction failed: {e}]", []

    interactive = data.get("interactive", [])
    headings = data.get("headings", [])
    visible_text = data.get("visibleText", "")

    title = await page.title()

    # Build formatted output
    lines = [
        f"URL: {page.url}",
        f"Title: {title}",
        "---",
    ]

    # Add headings for context
    if headings:
        lines.append("Page structure:")
        for h in headings[:10]:  # Cap at 10 headings
            indent = "  " * (h["level"] - 1)
            lines.append(f'  {indent}h{h["level"]}: "{h["text"]}"')
        lines.append("")

    # Add page text snippet for content understanding
    if visible_text:
        # Truncate to first ~200 chars
        snippet = visible_text[:200].replace('\n', ' ').strip()
        lines.append(f"Page content preview: {snippet}")
        lines.append("")

    # Group elements by section for clarity
    sections = {}
    for i, elem in enumerate(interactive):
        sec = elem.get("section", "MAIN")
        if sec not in sections:
            sections[sec] = []
        sections[sec].append((i, elem))

    # Order: MAIN first (most important), then others
    section_order = ["MAIN", "SIDEBAR", "DIALOG", "HEADER", "NAV", "FOOTER"]

    lines.append(f"Interactive elements ({len(interactive)} total):")

    for sec in section_order:
        if sec not in sections:
            continue
        items = sections[sec]

        # Label sections for context
        if sec != "MAIN":
            lines.append(f"  --- [{sec}] ---")

        for i, elem in items:
            extras = []
            if elem.get("focused"):
                extras.append("FOCUSED")
            if elem.get("checked"):
                extras.append("CHECKED")
            if elem.get("disabled"):
                extras.append("DISABLED")
            if elem.get("value"):
                extras.append(f'value="{elem["value"][:50]}"')
            if elem.get("href"):
                extras.append(f'href="{elem["href"][:60]}"')

            extra_str = f' [{", ".join(extras)}]' if extras else ""
            name_display = elem["name"][:80] if elem["name"] else "(unnamed)"

            lines.append(f'  [{i}] {elem["role"]}: "{name_display}"{extra_str}')

    formatted = "\n".join(lines)
    logger.info("page state: %d interactive elements, %d chars", len(interactive), len(formatted))
    return formatted, interactive


async def take_screenshot(page: Page) -> str | None:
    """
    Take a screenshot and return as base64 string.
    Only called when the DOM extraction fails or agent is stuck.
    """
    try:
        screenshot_bytes = await page.screenshot(full_page=False)
        b64 = base64.b64encode(screenshot_bytes).decode("utf-8")
        logger.info("screenshot taken: %d bytes", len(screenshot_bytes))
        return b64
    except Exception as e:
        logger.error("screenshot failed: %s", e)
        return None
