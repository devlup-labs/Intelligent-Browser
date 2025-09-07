"""
FastMCP quickstart example.

cd to the `examples/snippets/clients` directory and run:
    uv run server fastmcp_quickstart stdio
"""

from mcp.server.fastmcp import FastMCP
import time
from playwright.async_api import Page, Browser, async_playwright, Error as PlaywrightError
from typing import Dict, List, Optional
from bs4 import BeautifulSoup, NavigableString, Comment
import re
import httpx
# import requests


# Create an MCP server
mcp = FastMCP("GoodDemo")

page = None
browser = None

async def _get_element_positions() -> Dict[str, Dict]:
    """Get positions of interactive elements"""
    js_code = """
    () => {
        const positions = {};
        const interactiveSelectors = [
            'a', 'button', 'input', 'textarea', 'select', 'form', 
            'label', 'details', 'summary', 'dialog'
        ];
        
        // Also check for elements with button-like classes
        const buttonClassIndicators = ['button', 'btn', 'clickable', 'link-button'];
        
        let elementCounter = 0;
        
        // Get traditional interactive elements
        interactiveSelectors.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach((el) => {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width > 0 && rect.height > 0 && style.opacity > 0 && style.visibility !== 'hidden') {
                    const uniqueId = el.getAttribute('data-cleaner-id') || `cleaner-id-${elementCounter}`;
                    if (!el.getAttribute('data-cleaner-id')) {
                        el.setAttribute('data-cleaner-id', uniqueId);
                    }
                    
                    positions[uniqueId] = {
                        x: Math.round(rect.left + window.scrollX),
                        y: Math.round(rect.top + window.scrollY),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        tag: el.tagName.toLowerCase(),
                        text: el.textContent.trim().replace(/\\s+/g, ' '),
                    };
                    elementCounter++;
                }
            });
        });
        
        // Get elements with button-like classes
        buttonClassIndicators.forEach(indicator => {
            const elements = document.querySelectorAll(`[class*="${indicator}"]`);
            elements.forEach((el) => {
                // Skip if already processed
                if (el.getAttribute('data-cleaner-id')) return;
                
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                if (rect.width > 0 && rect.height > 0 && style.opacity > 0 && style.visibility !== 'hidden') {
                    const uniqueId = `cleaner-id-${elementCounter}`;
                    el.setAttribute('data-cleaner-id', uniqueId);
                    
                    positions[uniqueId] = {
                        x: Math.round(rect.left + window.scrollX),
                        y: Math.round(rect.top + window.scrollY),
                        w: Math.round(rect.width),
                        h: Math.round(rect.height),
                        tag: el.tagName.toLowerCase(),
                        text: el.textContent.trim().replace(/\\s+/g, ' '),
                    };
                    elementCounter++;
                }
            });
        });
        
        return positions;
    }
    """
    
    try:
        positions = await page.evaluate(js_code)
        return positions
    except Exception as e:
        return {}

def _clean_html(html_content: str, element_positions: Dict) -> str:
    """Clean HTML content for LLM consumption"""
    # Define element sets
    interactive_elements = {
        'a', 'button', 'input', 'textarea', 'select', 'option', 
        'form', 'label', 'details', 'summary', 'dialog'
    }
    
    content_elements = {
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div',
        'article', 'section', 'main', 'aside', 'nav', 'header', 'footer',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd', 'blockquote', 'pre', 'code',
        'strong', 'em', 'b', 'i', 'mark', 'small', 'sub', 'sup'
    }
    
    list_elements = {'ul', 'ol', 'li'}
    
    interactive_attributes = {
        'id', 'name', 'type', 'value', 'placeholder', 'href',
        'action', 'method', 'for', 'role', 'aria-label', 'title',
        'disabled', 'readonly', 'required', 'checked', 'selected', 'class'
    }

    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    unwanted_tags = [
        'script', 'style', 'link', 'meta', 'noscript', 'iframe',
        'embed', 'object', 'applet', 'canvas', 'svg', 'audio', 'video'
    ]
    
    for tag_name in unwanted_tags:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # Handle images
    for img_tag in soup.find_all('img'):
        alt_text = img_tag.get('alt', '').strip()
        if alt_text:
            img_tag.insert_before(f"[Image: {alt_text}]")
        img_tag.decompose()
    
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    if not soup.body:
        return "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"UTF-8\">\n<title>Cleaned for LLM</title>\n</head>\n<body>\n</body>\n</html>"
    
    # Find innermost interactive elements
    innermost_interactive = set()
    all_interactive = []
    
    # Get traditional interactive elements
    for tag_name in interactive_elements:
        all_interactive.extend(soup.body.find_all(tag_name))
    
    # Also find elements with button-like classes
    button_class_indicators = ['button', 'btn', 'clickable', 'link-button', 'ui button']
    for indicator in button_class_indicators:
        elements_with_class = soup.body.find_all(class_=lambda x: x and indicator in ' '.join(x).lower())
        all_interactive.extend(elements_with_class)
    
    for element in all_interactive:
        has_interactive_children = False
        for child_tag in interactive_elements:
            if element.find_all(child_tag):
                has_interactive_children = True
                break
        
        if not has_interactive_children:
            innermost_interactive.add(element)

    # Process elements
    result = []
    for element in soup.body.children:
        _process_element(element, result, element_positions, innermost_interactive, 
                            interactive_elements, content_elements, list_elements, interactive_attributes)
    
    # Create final HTML
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="UTF-8">',
        '<title>Cleaned for LLM</title>',
        '</head>',
        '<body>'
    ]
    
    for element in result:
        try:
            if isinstance(element, dict) and element.get('type') == 'interactive':
                tag = element.get('tag', '')
                attrs = element.get('attributes', {})
                text = element.get('text', '')
                
                attr_string = ''
                for key, value in attrs.items():
                    escaped_value = str(value).replace('"', '&quot;')
                    attr_string += f' {key}="{escaped_value}"'
                
                if tag in ['input', 'img', 'br', 'hr']:
                    html_parts.append(f'<{tag}{attr_string}/>')
                else:
                    escaped_text = str(text).replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(f'<{tag}{attr_string}>{escaped_text}</{tag}>')
            
            elif isinstance(element, dict) and 'tag' in element and 'text' in element:
                tag = element['tag']
                text = element['text']
                if text.strip():
                    escaped_text = text.replace('<', '&lt;').replace('>', '&gt;')
                    html_parts.append(f'<{tag}>{escaped_text}</{tag}>')
            
            elif isinstance(element, str):
                if element.strip():
                    escaped_text = element.replace('<', '&lt;').replace('>', '&gt;')
                    if len(escaped_text.strip()) < 10:
                        html_parts.append(f'<span>{escaped_text}</span>')
                    else:
                        html_parts.append(f'<p>{escaped_text}</p>')
        except Exception as e:
            continue
    
    html_parts.extend(['</body>', '</html>'])
    return '\n'.join(html_parts)

def _process_element(element, result: List, element_positions: Dict, innermost_interactive: set,
                    interactive_elements: set, content_elements: set, list_elements: set, interactive_attributes: set):
    """Process a single element"""
    # Handle text nodes
    if isinstance(element, NavigableString):
        text = str(element).strip()
        if text:
            result.append(text)
        return
    
    # Skip non-element nodes
    if not hasattr(element, 'name') or not element.name:
        return

    tag_name = element.name.lower()
    
    # If this is an innermost interactive element, process it
    if element in innermost_interactive:
        interactive_data = _create_interactive_element(element, element_positions, interactive_attributes)
        if interactive_data:
            result.append(interactive_data)
        return
    
    # If this is a non-innermost interactive element, skip it and process children
    if tag_name in interactive_elements:
        for child in element.children:
            _process_element(child, result, element_positions, innermost_interactive,
                                interactive_elements, content_elements, list_elements, interactive_attributes)
        return
    
    # Handle list elements specially - merge if text-only
    if tag_name in list_elements:
        if not _contains_innermost_interactive(element, innermost_interactive):
            list_text = _extract_list_text(element)
            if list_text:
                result.append({
                    'tag': tag_name,
                    'text': list_text,
                    'attributes': {}
                })
            return
    
    # Handle content elements
    if tag_name in content_elements:
        if not _contains_innermost_interactive(element, innermost_interactive):
            text_content = element.get_text(strip=True)
            if text_content:
                if len(text_content) > 200 and tag_name == 'div':
                    chunks = _split_long_text(text_content)
                    for chunk in chunks:
                        if chunk.strip():
                            result.append({
                                'tag': 'p',
                                'text': re.sub(r'\s+', ' ', chunk.strip()),
                                'attributes': {}
                            })
                else:
                    result.append({
                        'tag': tag_name,
                        'text': re.sub(r'\s+', ' ', text_content),
                        'attributes': {}
                    })
            return
        else:
            for child in element.children:
                _process_element(child, result, element_positions, innermost_interactive,
                                    interactive_elements, content_elements, list_elements, interactive_attributes)
            return
    
    # For other elements, just process children
    for child in element.children:
        _process_element(child, result, element_positions, innermost_interactive,
                            interactive_elements, content_elements, list_elements, interactive_attributes)

def _extract_list_text(element) -> str:
    """Extract and format text from list elements"""
    if element.name.lower() in ['ul', 'ol']:
        items = []
        for li in element.find_all('li', recursive=False):
            text = li.get_text(strip=True)
            if text:
                items.append(text)
        return ' | '.join(items)
    else:
        return element.get_text(strip=True)

def _split_long_text(text: str) -> List[str]:
    """Split long merged text into meaningful chunks"""
    chunks = []
    sentences = re.split(r'[.!?]+\s+', text)
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) > 150 and current_chunk:
            chunks.append(current_chunk)
            current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += ". " + sentence
            else:
                current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk)
    
    final_chunks = []
    for chunk in chunks:
        if len(chunk) > 150:
            parts = re.split(r'(?=[A-Z][a-z])', chunk)
            temp_chunk = ""
            for part in parts:
                if len(temp_chunk) + len(part) > 150 and temp_chunk:
                    final_chunks.append(temp_chunk.strip())
                    temp_chunk = part
                else:
                    temp_chunk += part
            if temp_chunk:
                final_chunks.append(temp_chunk.strip())
        else:
            final_chunks.append(chunk)
    
    return final_chunks if final_chunks else [text]

def _contains_innermost_interactive(element, innermost_interactive: set) -> bool:
    """Check if element contains any innermost interactive elements"""
    for interactive_el in innermost_interactive:
        if interactive_el in element.descendants:
            return True
    return False

def _create_interactive_element(element, element_positions: Dict, interactive_attributes: set) -> Optional[Dict]:
    """Create a cleaned interactive element with position data"""
    if not element or not hasattr(element, 'name') or not element.name:
        return None
    
    tag_name = element.name.lower()
    cleaner_id = element.get('data-cleaner-id')
    position_data = element_positions.get(cleaner_id)
    
    if not position_data:
        return None
    
    attrs = {
        'x': position_data['x'],
        'y': position_data['y'],
        'w': position_data['w'],
        'h': position_data['h']
    }
    
    try:
        for attr, value in element.attrs.items():
            if attr in interactive_attributes:
                if isinstance(value, list):
                    attrs[attr] = ' '.join(str(v) for v in value)
                else:
                    attrs[attr] = str(value) if value is not None else ''
    except Exception as e:
        pass
    
    text_content = element.get_text(strip=True) or position_data.get('text', '')
    
    # Skip elements with no meaningful text content (except inputs)
    if not text_content and tag_name not in ['input', 'textarea', 'select']:
        return None
    
    return {
        'tag': tag_name,
        'attributes': attrs,
        'text': text_content,
        'type': 'interactive'
    }


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
    
# @mcp.tool()
# async def ClickElementTool(selector: str, wait_for_navigation: bool = False):
#     """Click on an element specified by a CSS selector"""
#     global page
#     try:
#         element = await page.query_selector(selector)
#         if not element:
#             return f"Element with selector '{selector}' not found."
        
#         await element.click()
#         if wait_for_navigation:
#             await page.wait_for_navigation(wait_until='load')
#         return f"Clicked on element with selector '{selector}'."
#     except PlaywrightError as e:
#         return f"Click action failed due to browser error: {e}"
#     except TimeoutError as e:
#         return f"Click action timed out: {e}"
    
@mcp.tool()
async def FillInputTool(selector: str, value: str):
    """Fill an input field specified by a CSS selector with a given value"""
    global page
    try:
        element = await page.query_selector(selector)
        if not element:
            return f"Input field with selector '{selector}' not found."
        
        await element.fill(value)
        return f"Filled input field with selector '{selector}' with value '{value}'."
    except PlaywrightError as e:
        return f"Fill action failed due to browser error: {e}"
    except TimeoutError as e:
        return f"Fill action timed out: {e}"
    
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

# # Add a dynamic greeting resource
# @mcp.resource("greeting://{name}")
# def get_greeting(name: str) -> str:
#     """Get a personalized greeting"""
#     return f"Hello, {name}!"


# # Add a prompt
# @mcp.prompt()
# def greet_user(name: str, style: str = "friendly") -> str:
#     """Generate a greeting prompt"""
#     styles = {
#         "friendly": "Please write a warm, friendly greeting",
#         "formal": "Please write a formal, professional greeting",
#         "casual": "Please write a casual, relaxed greeting",
#     }

#     return f"{styles.get(style, styles['friendly'])} for someone named {name}."

async def normalizeToPixels(viewportSize: dict, normalizedCoord: list)->list:
    width = viewportSize['width']
    height = viewportSize['height']
    x = int(normalizedCoord[0] * width)
    y = int(normalizedCoord[1] * height)
    return [x, y]