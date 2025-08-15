import json
import os
import re
import base64
import time
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playwright.sync_api import sync_playwright

JWT_DB_FILE = "jwt_store.json"  # file to store JWT + expiry


# -------------------------
# Utility: decode JWT exp
# -------------------------
def decode_jwt_exp(jwt_token):
    try:
        payload_b64 = jwt_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)  # pad
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        return payload.get("exp")  # Unix timestamp
    except Exception as e:
        print("Error decoding JWT:", e)
        return None
    
    print()


# -------------------------
# Selector Extractor Tool
# -------------------------
class SelectorExtractorInput(BaseModel):
    parsed_html: str = Field(..., description="Parsed HTML with only interactive elements")


class SelectorExtractorTool(BaseTool):
    name: str = "selector_extractor"
    description: str = "Extracts selectors for username, password, and submit button from parsed HTML."
    args_schema: type[BaseModel] = SelectorExtractorInput

    def _run(self, parsed_html: str) -> dict:
        username_selector = self._find_selector(parsed_html, r'(?:id|name)="?(?:username|user|login|email)[^"\s>]*"?')
        password_selector = self._find_selector(parsed_html, r'(?:id|name)="?(?:password|pass)[^"\s>]*"?')
        submit_selector = self._find_selector(parsed_html, r'(?:id|name)="?(?:submit|login|sign)[^"\s>]*"?')

        return {
            "username_selector": username_selector or "",
            "password_selector": password_selector or "",
            "submit_selector": submit_selector or "text=Login"
        }

    def _find_selector(self, html: str, pattern: str):
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            attr_value = match.group().split("=")[-1].strip('"').strip("'")
            if "id=" in match.group().lower():
                return f"#{attr_value}"
            else:
                return f"[name='{attr_value}']"
        return None


# -------------------------
# Playwright Login Tool
# -------------------------
class PlaywrightLoginInput(BaseModel):
    page: object
    url: str
    username: str
    password: str
    username_selector: str
    password_selector: str
    submit_selector: str


class PlaywrightLoginTool(BaseTool):
    name: str = "playwright_login"
    description: str = "Logs into a site using Playwright without extracting JWT."
    args_schema: type[BaseModel] = PlaywrightLoginInput

    def _run(self, page, url, username, password, username_selector, password_selector, submit_selector):
        try:
            page.goto(url)
            page.fill(username_selector, username)
            page.fill(password_selector, password)
            page.click(submit_selector)
            page.wait_for_timeout(5000)  # wait for login to process
            return f"Login completed for {url}"
        except Exception as e:
            return f"Login failed: {str(e)}"


# -------------------------
# Smart Login Tool
# -------------------------
class SmartLoginInput(BaseModel):
    url: str
    parsed_html: str
    page: object


from playwright.sync_api import sync_playwright

class SmartLoginTool(BaseTool):
    name: str = "smart_login"
    description: str = "Logs into a site using JWT if available & not expired, else creds, stores new JWT with expiry."
    args_schema: type[BaseModel] = SmartLoginInput

    def _run(self, url, parsed_html, page):
        # jwt_data = self._get_jwt(url)

        # # 1️⃣ If JWT exists and is still valid
        # if jwt_data and time.time() < jwt_data["expires_at"]:
        #     print("✅ Using stored valid JWT")
        #     self._inject_jwt(page, jwt_data["token"])
        #     return f"Used stored JWT token for {url} → login successful"

        # print("⚠️ No valid JWT found, logging in with credentials...")

        # 2️⃣ Get credentials
    #    creds = self._get_credentials(url)
        creds = False
        if not creds:
            username = input("Enter username: ")
            password = input("Enter password: ")
            creds = {"username": username, "password": password}
           # self._save_credentials(url, username, password)

        # 3️⃣ Extract selectors
        selectors = SelectorExtractorTool()._run(parsed_html)

        # 4️⃣ Perform login in same browser
        PlaywrightLoginTool()._run(
            page=page,
            url=url,
            username=creds["username"],
            password=creds["password"],
            username_selector=selectors["username_selector"],
            password_selector=selectors["password_selector"],
            submit_selector=selectors["submit_selector"]
        )

        # 5️⃣ Extract new JWT
        new_jwt = self._extract_jwt(page)

        if new_jwt:
            exp_time = decode_jwt_exp(new_jwt)
            if not exp_time:
                exp_time = time.time() + 3600  # fallback: 1h
        #    self._save_jwt(url, new_jwt, exp_time)
            print(f"💾 Saved new JWT, expires at {time.ctime(exp_time)}")
        else:
            print("❌ Could not extract JWT after login")
            print()
        return f"Login completed for {url} with new JWT"

    # -------------------------
    # Helper functions
    # -------------------------
    def _inject_jwt(self, page, jwt_token):
        page.evaluate(f"""
            () => {{
                localStorage.setItem("jwt", "{jwt_token}");
            }}
        """)
        page.reload()
        page.wait_for_timeout(2000)

    def _extract_jwt(self, page):
        """Read JWT from localStorage."""
        return page.evaluate("""() => localStorage.getItem("jwt")""")

    # -------------------------
    # "Database" functions
    # -------------------------
    # def _get_jwt(self, url):
    #     if not os.path.exists(JWT_DB_FILE):
    #         return None
    #     with open(JWT_DB_FILE, "r") as f:
    #         data = json.load(f)
    #     return data.get(url)

    # def _save_jwt(self, url, token, expires_at):
    #     if os.path.exists(JWT_DB_FILE):
    #         with open(JWT_DB_FILE, "r") as f:
    #             data = json.load(f)
    #     else:
    #         data = {}
    #     data[url] = {"token": token, "expires_at": expires_at}
    #     with open(JWT_DB_FILE, "w") as f:
    #         json.dump(data, f)

    # def _get_credentials(self, url):
    #     # Replace with secure storage logic if needed
    #     return None

    # def _save_credentials(self, url, username, password):
    #     print(f"💾 Saved credentials for {url} → ({username}, ****)")
