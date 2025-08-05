from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playwright.async_api import Page, Error as PlaywrightError
from bs4 import BeautifulSoup, NavigableString, Comment
import re
from typing import Dict, List, Optional

class GoToPageSchema(BaseModel):
    url: str = Field(..., description="The full URL to navigate to (e.g., https://www.google.com).")

class TakeScreenshotSchema(BaseModel):
    ss_name: str = Field(default="screenshot.png", description="The name of the screenshot file to be saved(e.g., notionloginpage.png).")
    full_page: bool = Field(default=False, description="Whether to capture the full page screenshot or just the viewport.")

class ClickElementSchema(BaseModel):
    selector: str = Field(..., description="The CSS selector of the element to click.")
    wait_for_navigation: bool = Field(False, description="Whether to wait for navigation after clicking the element.")

class FillInputSchema(BaseModel):
    selector: str = Field(..., description="The CSS selector of the input field to fill.")
    value: str = Field(..., description="The value to fill into the input field.")

class HoverElementInput(BaseModel):
    selector: str

class DoubleCLickSchema(BaseModel):
    selector: str = Field(..., description="The CSS selector of the element to double-click.")

class ScrollPageSchema(BaseModel):
    direction: str = Field(..., description="The direction to scroll the page ('up' or 'down').")

class TextDeleteSchema(BaseModel):
    text: str = Field(..., description="The text to delete from the input field or textarea.")

class FetchAndCleanHTMLSchema(BaseModel):
    url: str = Field(..., description="URL parameter (not used - tool works on current page content)")

class SelectDropdownInput(BaseModel):
    selector: str
    option_value: Optional[str] = None
    option_label: Optional[str] = None
    option_index: Optional[int] = None

class EmptySchema(BaseModel):
    pass  

class TakeScreenshotTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = TakeScreenshotSchema
    page: Page

    async def _run(self, ss_name: str, full_page: bool) -> str:
        try:
            screenshot_options = {
                "full_page": full_page,
                "path": ss_name if ss_name.endswith('.png') else f"{ss_name}.png"
            }
            screenshot_bytes = await self.page.screenshot(**screenshot_options)
            # base64_image = base64.b64encode(screenshot_bytes).decode('utf-8')
            # return f"""Image: data:image/png;base64,{base64_image}
            # The screenshot shows the current state of the webpage. You can now:
            # - Analyze the visual content and layout
            # - Identify buttons, links, forms, and interactive elements
            # - Read text content and navigation menus
            # - Determine the next action to take
            # - Locate specific elements for clicking or interaction"""
        except PlaywrightError as e:
            return f"Failed to take screenshot due to browser error: {e}"
        except Exception as e:
            return f"An unexpected error occurred while taking screenshot: {e}"

class HoverElementInput(BaseModel):
    selector: str

class SelectDropdownInput(BaseModel):
    selector: str
    option_value: Optional[str] = None
    option_label: Optional[str] = None
    option_index: Optional[int] = None

class FetchAndCleanHTMLSchema(BaseModel):
    url: str = Field(..., description="URL parameter (not used - tool works on current page content)")

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
        
class ClickElementTool(BaseTool):
    name: str 
    description: str
    args_schema: type[BaseModel] = ClickElementSchema
    page: Page

    async def _run(self, selector: str, wait_for_navigation: bool = False) -> str:
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return f"Element with selector '{selector}' not found."
            
            await element.click()
            if wait_for_navigation:
                await self.page.wait_for_navigation(wait_until='load')
            return f"Clicked on element with selector '{selector}'."
        except PlaywrightError as e:
            return f"Click action failed due to browser error: {e}"
        except TimeoutError as e:
            return f"Click action timed out: {e}"
        
class FillInputTool(BaseTool):
    name: str 
    description: str
    args_schema: type[BaseModel] = FillInputSchema
    page: Page

    async def _run(self, selector: str, value: str) -> str:
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return f"Input field with selector '{selector}' not found."
            
            await element.fill(value)
            return f"Filled input field with selector '{selector}' with value '{value}'."
        except PlaywrightError as e:
            return f"Fill action failed due to browser error: {e}"
        except TimeoutError as e:
            return f"Fill action timed out: {e}"
        
class GoBackTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = EmptySchema #no input is needed to go back
    page: Page

    async def _run(self) -> str:
        try:
            await self.page.go_back(wait_until='load')
            return "Successfully went back to previous page."
        except PlaywrightError as e:
            return f"Failed to go back due to error: {e}"
        except TimeoutError as e:
            return f"Going back timed out:{e}"

class ReloadPageTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = EmptySchema #no input is needed for reload
    page: Page

    async def _run(self) -> str:
        try:
            await self.page.reload(wait_until= 'load')
            return "Page reloaded successfully"
        except PlaywrightError as e:
            return f"Reload failed due to browser error:{e}"
        except TimeoutError as e:
            return f"Page reload timed out: {e}"
        

class GetCurrentURL(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel]= EmptySchema #no input needed
    page: Page

    async def _run(self) -> str:
        try:
            return f"Current page URL: {self.page.url}"
        except PlaywrightError as e:
            return f"Failed to retrieve current URL due to broser error: {e}"        
        

class HoverElementTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel]= HoverElementInput
    page: Page

    async def _run(self, selector:str) -> str:
        try:
            await self.page.hover(selector)
            return f"Hovered over element: {selector}"
        except PlaywrightError as e:
            return f"Failed to hover due to browser error: {e}"
        except TimeoutError as e:
            return f"Hover action timed out: {e}"


class SelectDropdownTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = SelectDropdownInput
    page: Page

    async def _run(self, selector:str, option_value: Optional[str]= None, option_label: Optional[str]= None, option_index: Optional[int]= None) -> str:
        try:
            if option_value:
                await self.page.select_option(selector, value= option_value)
                return f"Selected option with value: {option_value}"
            
            elif option_label:
                await self.page.select_option(selector, label= option_label)
                return f"Selected option with label: {option_label}"
            
            elif option_index:
                await self.page.select_option(selector, index= option_index)
                return f"Selected option with index: {option_index}"
            
            else:
                return "No valid option provided. Please specify value, label or index."
            

        except PlaywrightError as e:
            return f"Dropdown selection failed: {e}"
        except TimeoutError as e:
            return f"Timeout while selecting from dropdown: {e}"    



class TextDeleteTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = TextDeleteSchema
    page: Page

    async def _run(self, text: str) -> str:
        try:
            element = await self.page.query_selector('input[type="text"], textarea')
            await self.page.evaluate(f'element.innerText = element.innerText.replace("{text}", "");')
            return f"Successfully deleted text: {text}"
        except PlaywrightError as e:
            return f"Failed to delete text due to browser error: {e}"
        except TimeoutError as e:
            return f"Text deletion timed out: {e}"



class DoubleClickTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = DoubleCLickSchema
    page: Page

    async def _run(self, selector: str) -> str:
        try:
            element = await self.page.query_selector(selector)
            if element:
                await element.dblclick()
                return f"Successfully double-clicked on the element with selector: {selector}"
            else:
                return f"No element found with selector: {selector}"
        except PlaywrightError as e:
            return f"Failed to double-click due to browser error: {e}"
        except TimeoutError as e:
            return f"Double-click action timed out: {e}"
        

class ScrollPageTool(BaseTool):
    name: str
    description: str
    args_schema: type[BaseModel] = ScrollPageSchema
    page: Page

    async def _run(self, direction: str) -> str:
        try:
            if direction not in ['up', 'down']:
                return "Invalid scroll direction. Please use 'up' or 'down'."

            await self.page.evaluate(f'window.scrollBy(0, {100 if direction == "down" else -100});')
            return f"Successfully scrolled {direction}."
        except PlaywrightError as e:
            return f"Failed to scroll due to browser error: {e}"
        except TimeoutError as e:
            return f"Scroll action timed out: {e}"


class FetchAndCleanHTMLTool(BaseTool):
    name: str 
    description: str 
    args_schema: type[BaseModel] = FetchAndCleanHTMLSchema
    page: Page

    async def _run(self, url: str) -> str:
        try:
            # Get element positions from current page
            element_positions = await self._get_element_positions()
            
            # Get HTML content from current page
            html_content = await self.page.content()
            
            # Clean HTML
            cleaned_html = self._clean_html(html_content, element_positions)
            
            return cleaned_html
            
        except Exception as e:
            return f"Failed to clean HTML from current page. Error: {e}"

    async def _get_element_positions(self) -> Dict[str, Dict]:
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
            positions = await self.page.evaluate(js_code)
            return positions
        except Exception as e:
            return {}

    def _clean_html(self, html_content: str, element_positions: Dict) -> str:
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
            self._process_element(element, result, element_positions, innermost_interactive, 
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

    def _process_element(self, element, result: List, element_positions: Dict, innermost_interactive: set,
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
            interactive_data = self._create_interactive_element(element, element_positions, interactive_attributes)
            if interactive_data:
                result.append(interactive_data)
            return
        
        # If this is a non-innermost interactive element, skip it and process children
        if tag_name in interactive_elements:
            for child in element.children:
                self._process_element(child, result, element_positions, innermost_interactive,
                                    interactive_elements, content_elements, list_elements, interactive_attributes)
            return
        
        # Handle list elements specially - merge if text-only
        if tag_name in list_elements:
            if not self._contains_innermost_interactive(element, innermost_interactive):
                list_text = self._extract_list_text(element)
                if list_text:
                    result.append({
                        'tag': tag_name,
                        'text': list_text,
                        'attributes': {}
                    })
                return
        
        # Handle content elements
        if tag_name in content_elements:
            if not self._contains_innermost_interactive(element, innermost_interactive):
                text_content = element.get_text(strip=True)
                if text_content:
                    if len(text_content) > 200 and tag_name == 'div':
                        chunks = self._split_long_text(text_content)
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
                    self._process_element(child, result, element_positions, innermost_interactive,
                                        interactive_elements, content_elements, list_elements, interactive_attributes)
                return
        
        # For other elements, just process children
        for child in element.children:
            self._process_element(child, result, element_positions, innermost_interactive,
                                interactive_elements, content_elements, list_elements, interactive_attributes)

    def _extract_list_text(self, element) -> str:
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

    def _split_long_text(self, text: str) -> List[str]:
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

    def _contains_innermost_interactive(self, element, innermost_interactive: set) -> bool:
        """Check if element contains any innermost interactive elements"""
        for interactive_el in innermost_interactive:
            if interactive_el in element.descendants:
                return True
        return False

    def _create_interactive_element(self, element, element_positions: Dict, interactive_attributes: set) -> Optional[Dict]:
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


