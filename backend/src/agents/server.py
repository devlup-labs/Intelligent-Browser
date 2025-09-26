from mcp.server.fastmcp import FastMCP
import time
from playwright.async_api import Page, Browser, async_playwright, Error as PlaywrightError
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, NavigableString, Comment
import re
import httpx
from utils.ExtraFunctions import _clean_html, _contains_innermost_interactive, _create_interactive_element, _extract_list_text, _get_element_positions, _process_element, _split_long_text, normalizeToPixels

mcp = FastMCP("GoodDemo")

page = None
browser = None


# Add an addition tool
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
async def StartBrowserSession():
    """Start a new browsers session at the beginning"""
    try:
        global page
        global browser
        p = await async_playwright().start()
        browser = await p.chromium.launch(headless=False)
        PAGE = await browser.new_page()
        page = PAGE
        return f"Browser initiated successfully"
    except Exception as e:
        return e
        await browser.close()

@mcp.tool()
async def GetCurrentURL():
    """Get the current URL of the page"""
    global page
    try:
        return f"Current page URL: {page.url}"
    except PlaywrightError as e:
        return f"Failed to retrieve current URL due to broser error: {e}" 


@mcp.tool()
async def GoToUrlTool(url: str):
    """Navigate to a specified URL"""
    try:
        global page
        await page.goto(url, wait_until='load')
        return f"Successfully navigated to {url}. The page content is now available."
    except PlaywrightError as e:
        return f"Navigation failed due to browser error: {e}"
    except TimeoutError as e:
        return f"Navigation to {url} timed out: {e}"
    
@mcp.tool()
async def TakeScreenshotTool(ss_name: str, full_page: bool):
    """Take a screenshot of the current page"""
    global page
    try:
        screenshot_options = {
            "full_page": full_page,
            "path": ss_name if ss_name.endswith('.png') else f"{ss_name}.png"
        }
        screenshot_bytes = await page.screenshot(**screenshot_options)
    except PlaywrightError as e:
        return f"Failed to take screenshot due to browser error: {e}"
    except Exception as e:
        return f"An unexpected error occurred while taking screenshot: {e}"
    
@mcp.tool()
async def clickElementTool(ss_name: str, full_page: bool, task: str):
    """clicks the element requirted to perform the task for eg: task = 'click login button', the tool will click the login button"""
    global page
    history = []
    try:
        screenshot_options = {
            "full_page": full_page,
            "path": ss_name if ss_name.endswith('.png') else f"{ss_name}.png"
        }
        screenshot_bytes = await page.screenshot(**screenshot_options)
        with open(screenshot_options["path"], "rb") as f:
            files = {'file': (screenshot_options["path"], f, 'image/png')}
            async with httpx.AsyncClient() as requests:
                try:
                    response = await requests.post("http://10.36.16.15:8000/process-image/", data={"task": task, "history": history}, files=files)
                    # print(response.json())
                    action_code = response.json()
                    json = action_code['action_code']
                    cord = json['location']
                    pixelCords = await normalizeToPixels(page.viewport_size, cord)
                    await page.mouse.click(pixelCords[0], pixelCords[1])
                    time.sleep(2)
                    return f"completed task successfully"
                except Exception as e:
                    print(f"Failed to send image to server: {e}")
    except PlaywrightError as e:
        return f"Failed to take screenshot due to browser error: {e}"
    except Exception as e:
        return f"An unexpected error occurred while taking screenshot: {e}"
    
@mcp.tool()
async def TextInputTool(ss_name: str, full_page: bool, task: str, text_to_enter: str):
    """enters the given text_to_enter in the required field for e.g if task is to enter text in the search box and the text_to_enter is Artificial Intelligence then it will enter Artificail intelligence in the text box"""
    global page
    history = []
    try:
        screenshot_options = {
            "full_page": full_page,
            "path": ss_name if ss_name.endswith('.png') else f"{ss_name}.png"
        }
        screenshot_bytes = await page.screenshot(**screenshot_options)
        with open(screenshot_options["path"], "rb") as f:
            files = {'file': (screenshot_options["path"], f, 'image/png')}
            async with httpx.AsyncClient() as requests:
                try:
                    response = await requests.post("http://10.36.16.15:8000/process-image/", data={"task": task, "history": history}, files=files)
                    # print(response.json())
                    action_code = response.json()
                    json = action_code['action_code']
                    cord = json['location']
                    pixelCords = await normalizeToPixels(page.viewport_size, cord)
                    await page.mouse.click(pixelCords[0], pixelCords[1])
                    # time.sleep(2)
                    await page.wait_for_timeout(200)
                    await page.keyboard.press('Control+a')
                    await page.keyboard.press('Delete')
                    # print(f"Typing: '{text_to_enter}'")
                    await page.keyboard.type(text_to_enter)
                    return f"completed task successfully"
                except Exception as e:
                    print(f"Failed to send image to server: {e}")
    except PlaywrightError as e:
        return f"Failed to take screenshot due to browser error: {e}"
    except Exception as e:
        return f"An unexpected error occurred while taking screenshot: {e}"
    
@mcp.tool()
async def GoBackTool():
    """Navigate back to the previous page"""
    global page
    try:
        await page.go_back(wait_until='load')
        return "Successfully went back to previous page."
    except PlaywrightError as e:
        return f"Failed to go back due to error: {e}"
    except TimeoutError as e:
        return f"Going back timed out:{e}"
    
@mcp.tool()
async def ReloadPageTool():
    """Reload the current page"""
    global page
    try:
        await page.reload(wait_until= 'load')
        return "Page reloaded successfully"
    except PlaywrightError as e:
        return f"Reload failed due to browser error:{e}"
    except TimeoutError as e:
        return f"Page reload timed out: {e}"
    
@mcp.tool()
async def HoverElementTool(selector:str):
    """Hover over an element specified by a CSS selector"""
    global page
    try:
        await page.hover(selector)
        return f"Hovered over element: {selector}"
    except PlaywrightError as e:
        return f"Failed to hover due to browser error: {e}"
    except TimeoutError as e:
        return f"Hover action timed out: {e}"
    
@mcp.tool()
async def DropdownSelectionTool(selector:str, option_value: Optional[str]= None, option_label: Optional[str]= None, option_index: Optional[int]= None):
    """Select an option from a dropdown menu specified by a CSS selector"""
    global page
    try:
        if option_value:
            await page.select_option(selector, value= option_value)
            return f"Selected option with value: {option_value}"
        
        elif option_label:
            await page.select_option(selector, label= option_label)
            return f"Selected option with label: {option_label}"
        
        elif option_index:
            await page.select_option(selector, index= option_index)
            return f"Selected option with index: {option_index}"
        
        else:
            return "No valid option provided. Please specify value, label or index."
        

    except PlaywrightError as e:
        return f"Dropdown selection failed: {e}"
    except TimeoutError as e:
        return f"Timeout while selecting from dropdown: {e}" 
    
@mcp.tool()
async def HoverElementTool(text: str):
    global page
    try:
        element = await page.query_selector('input[type="text"], textarea')
        await page.evaluate(f'element.innerText = element.innerText.replace("{text}", "");')
        return f"Successfully deleted text: {text}"
    except PlaywrightError as e:
        return f"Failed to delete text due to browser error: {e}"
    except TimeoutError as e:
        return f"Text deletion timed out: {e}"
    
@mcp.tool()
async def TextDeleteTool(text: str, selector: str):
    global page
    try:
        # element = await page.query_selector('input[type="text"], textarea')
        await page.evaluate(f'selector.innerText = selector.innerText.replace("{text}", "");')
        return f"Successfully deleted text: {text}"
    except PlaywrightError as e:
        return f"Failed to delete text due to browser error: {e}"
    except TimeoutError as e:
        return f"Text deletion timed out: {e}"
    
@mcp.tool()
async def DoubleClickTool(selector: str):
    """Double-click on an element specified by a CSS selector"""
    global page
    try:
        element = await page.query_selector(selector)
        if element:
            await element.dblclick()
            return f"Successfully double-clicked on the element with selector: {selector}"
        else:
            return f"No element found with selector: {selector}"
    except PlaywrightError as e:
        return f"Failed to double-click due to browser error: {e}"
    except TimeoutError as e:
        return f"Double-click action timed out: {e}"
    
@mcp.tool()
async def getcontexttool():
    global page
    minimal_elements = await page.evaluate("""
        () => {
            function isActionable(e) {
                // Only visible and actionable tags
                const tag = e.tagName;
                return (
                    e.offsetParent !== null &&
                    (tag === 'BUTTON' || tag === 'A' || tag === 'INPUT' || tag === 'TEXTAREA' || e.tabIndex >= 0)
                );
            }
            let index = 0;
            return Array.from(document.querySelectorAll('button, a, input, textarea, [tabindex]'))
                .filter(isActionable)
                .map(el => ({
                    frame: 'main', // Add iframe logic if needed
                    index: index++,
                    type: el.tagName.toLowerCase(),
                    name: el.innerText?.trim() ||
                          el.getAttribute('aria-label') ||
                          el.getAttribute('placeholder') ||
                          el.name || el.id || '',
                }));
        }
    """)
    metadata_cache = {}
    for item in minimal_elements:
        selector = f":nth-match({item['type']}, {item['index'] + 1})"
        element = await page.query_selector(selector)
        if element:
            bounding = await element.bounding_box()
            attributes = await page.evaluate(
                """e => Array.from(e.attributes).reduce((a, v) => (a[v.name] = v.value, a), {})""",
                element
            )
            cache_key = f"{item['frame']}:{item['index']}"
            metadata_cache[cache_key] = {
                'attributes': attributes,
                'coordinates': [bounding['x'], bounding['y']] if bounding else None,
                'bounds': [bounding['x'], bounding['y'], bounding['width'], bounding['height']] if bounding else None,
                'outerHTML': await element.evaluate('el => el.outerHTML'),
            }
    returning_elements = str(minimal_elements[:101])
    return returning_elements
    
# @mcp.tool()
# async def FetchAndCleanHTMLTool(selector: str):
#     """Fetch and clean HTML content from the current page to identify CSS selectors to be used for other tools"""
#     global page
#     try:
#         # Get element positions from current page
#         element_positions = await _get_element_positions()
        
#         # Get HTML content from current page
#         html_content = await page.content()
        
#         # Clean HTML
#         cleaned_html = _clean_html(html_content, element_positions)
        
#         return cleaned_html
        
#     except Exception as e:
#         return f"Failed to clean HTML from current page. Error: {e}"