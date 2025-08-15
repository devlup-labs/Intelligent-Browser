# enhancedtools.py
import os
import re
import json
import base64
import time
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from playwright.sync_api import sync_playwright

JWT_DB_FILE = "jwt_store.json"
CREDS_DB_FILE = "credentials_store.json"

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
    except Exception:
        return None


class SmartCombinedLoginInput(BaseModel):
    url: str = Field(..., description="Login page URL")
    parsed_html: str = Field(..., description="Parsed HTML snippet containing login form elements")


class SmartCombinedLoginTool(BaseTool):
    name: str = "smart_combined_login"
    description: str = (
        "Performs an intelligent login: tries stored JWT first, then stored credentials, then prompts user."
    )
    args_schema: type[BaseModel] = SmartCombinedLoginInput

    def _run(self, url, parsed_html):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # 1️⃣ Try JWT login
            # jwt_data = self._get_jwt(url)
            # if jwt_data and self._jwt_valid(jwt_data):
            #     self._inject_jwt(page, jwt_data["token"])
            #     page.goto(url)
            #     page.wait_for_timeout(3000)
            #     browser.close()
            #     return f"✅ Logged in using stored JWT for {url}"

            # 2️⃣ Try stored credentials
            # creds = self._get_credentials(url)
            # if creds:
            #     result = self._perform_login(page, url, parsed_html, creds["username"], creds["password"])
            #     browser.close()
            #     return result

            # 3️⃣ Ask user for credentials
            username = input("Enter username/email: ")
            password = input("Enter password: ")
            result = self._perform_login(page, url, parsed_html, username, password)
          #  self._save_credentials(url, username, password)
            browser.close()
            return result

    # -------------------------
    # Login process
    # -------------------------
    def _perform_login(self, page, url, parsed_html, username, password):
        selectors = self._extract_selectors(parsed_html)
        try:
            page.goto(url, timeout=30000)
            page.fill(selectors["username_selector"], username)
            page.fill(selectors["password_selector"], password)
            page.click(selectors["submit_selector"])
            page.wait_for_timeout(5000)

            jwt_token = self._extract_jwt(page)
            if jwt_token:
                exp = decode_jwt_exp(jwt_token)
                self._save_jwt(url, jwt_token, exp)
                return f"✅ Logged in using credentials, JWT saved for {url}"
            else:
                return f"⚠️ Logged in but no JWT found for {url}"
        except Exception as e:
            return f"❌ Login failed: {str(e)}"

    # -------------------------
    # Selector extraction
    # -------------------------
    def _extract_selectors(self, html: str) -> dict:
        username_selector = self._find_selector(html, r'(?:id|name)="?(?:username|user|login|email)[^"\s>]*"?')
        password_selector =_
