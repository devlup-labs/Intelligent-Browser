# Helper functions (not MCP tools - these are internal functions)
def find_selector_helper(html: str, pattern: str, fallback_type: str = None, fallback_button: bool = False):
    """Helper function to find selectors from HTML patterns."""
    try:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            attr_value = match.group().split("=")[-1].strip('"').strip("'")
            if "id=" in match.group().lower():
                return f"#{attr_value}"
            else:
                return f"[name='{attr_value}']"

        if fallback_type:
            if re.search(f'type=["\']{fallback_type}["\']', html, re.IGNORECASE):
                return f"input[type='{fallback_type}']"

        if fallback_button:
            if re.search(r"<button[^>]*>", html, re.IGNORECASE):
                return "button"
            if re.search(r"type=['\"]submit['\"]", html, re.IGNORECASE):
                return "button[type='submit']"
    except Exception as e:
        raise Exception(f"Error in find_selector_helper: {e}")
    
    return None

def extract_selectors_internal(parsed_html: str) -> dict:
    """Internal function to extract selectors - returns dict or raises exception."""
    try:
        selectors = {
            "username_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:username|user|login)[^"\s>]*"?', fallback_type="text"),
            "email_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:email)[^"\s>]*"?', fallback_type="email"),
            "password_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:password|pass)[^"\s>]*"?', fallback_type="password"),
            "otp_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:otp|code)[^"\s>]*"?', fallback_type="number"),
            "submit_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:submit|login|Sign in)[^"\s>]*"?', fallback_button=True)
        }

        if not selectors["submit_selector"]:
            selectors["submit_selector"] = "button[type='submit'], text=Login, text=Sign in"

        return selectors
    except Exception as e:
        raise Exception(f"Error extracting selectors: {e}")

def playwright_login_internal(page: Page, url: str, credentials: dict, selectors: dict) -> bool:
    """Internal function to perform login - returns bool or raises exception."""
    try:
        page.goto(url)

        if selectors.get("username_selector") and credentials.get("username"):
            try:
                username = fernet.decrypt(credentials["username"].encode()).decode()
                page.fill(selectors["username_selector"], username)
            except Exception as e:
                raise Exception(f"Error filling username field: {e}")

        # email
        if selectors.get("email_selector") and credentials.get("email"):
            try:
                email = fernet.decrypt(credentials["email"].encode()).decode()
                page.fill(selectors["email_selector"], email)
            except Exception as e:
                raise Exception(f"Error filling email field: {e}")

        # password
        if selectors.get("password_selector") and credentials.get("password"):
            try:
                password = fernet.decrypt(credentials["password"].encode()).decode()
                page.fill(selectors["password_selector"], password)
            except Exception as e:
                raise Exception(f"Error filling password field: {e}")

        # otp
        if selectors.get("otp_selector") and credentials.get("otp"):
            try:
                otp = fernet.decrypt(credentials["otp"].encode()).decode()
                page.fill(selectors["otp_selector"], otp)
            except Exception as e:
                raise Exception(f"Error filling OTP field: {e}")

        # Submit form
        try:
            if selectors.get("submit_selector"):
                try:
                    page.click("button[type='submit']")
                except:
                    page.press("input[name='password']", "Enter")
            else:
                page.keyboard.press("Enter")
        except Exception as e:
            raise Exception(f"Error submitting form: {e}")
            
        # Small wait for navigation/requests
        page.wait_for_timeout(4000)
        return True
    except Exception as e:
        raise Exception(f"Login process failed: {e}")

def find_jwt_anywhere_helper(page: Page):
    """Helper function to find JWT tokens anywhere on the page."""
    try:
        jwt_pattern = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
        found_tokens = []

        def handle_response(response):
            try:
                body = response.text()
                match = jwt_pattern.search(body)
                if match:
                    token = match.group()
                    found_tokens.append((f"network:{response.url}", token))
            except:
                pass

        page.on("response", handle_response)
        time.sleep(2)

        # localStorage
        try:
            storage_items = page.evaluate("""() => {
                let items = {};
                for (let i = 0; i < localStorage.length; i++) {
                    let key = localStorage.key(i);
                    items[`localStorage:${key}`] = localStorage.getItem(key);
                }
                return items;
            }""")
            for key, value in storage_items.items():
                if value and jwt_pattern.search(value):
                    found_tokens.append((key, jwt_pattern.search(value).group()))
        except Exception as e:
            raise Exception(f"Error checking localStorage for JWT: {e}")

        # sessionStorage
        try:
            session_items = page.evaluate("""() => {
                let items = {};
                for (let i = 0; i < sessionStorage.length; i++) {
                    let key = sessionStorage.key(i);
                    items[`sessionStorage:${key}`] = sessionStorage.getItem(key);
                }
                return items;
            }""")
            for key, value in session_items.items():
                if value and jwt_pattern.search(value):
                    found_tokens.append((key, jwt_pattern.search(value).group()))
        except Exception as e:
            raise Exception(f"Error checking sessionStorage for JWT: {e}")

        # cookies
        try:
            cookies = page.context.cookies()
            for c in cookies:
                if jwt_pattern.search(c['value']):
                    found_tokens.append((f"cookie:{c['name']}", jwt_pattern.search(c['value']).group()))
        except Exception as e:
            raise Exception(f"Error checking cookies for JWT: {e}")

        if found_tokens:
            seen = set()
            for source, token in found_tokens:
                if token not in seen:
                    seen.add(token)
                    if source.startswith('localStorage:'):
                        key_name = source.split(':', 1)[1]
                        return token, f"localStorage:{key_name}"
                    if source.startswith('sessionStorage:'):
                        key_name = source.split(':', 1)[1]
                        return token, f"sessionStorage:{key_name}"
                    if source.startswith('cookie:') or source.startswith('network:'):
                        return token, source
        return None, None
    except Exception as e:
        raise Exception(f"Error finding JWT tokens: {e}")

# MCP Tools (Only the main smart_login tool)
@mcp.tool()
def extract_selectors(parsed_html: str) -> str:
    """Extracts selectors for all possible login-related fields from parsed HTML and returns status message."""
    try:
        selectors = extract_selectors_internal(parsed_html)
        return f"✅ Successfully extracted selectors: username={selectors.get('username_selector')}, email={selectors.get('email_selector')}, password={selectors.get('password_selector')}, otp={selectors.get('otp_selector')}, submit={selectors.get('submit_selector')}"
    except Exception as e:
        return f"❌ Error extracting selectors: {e}"from playwright.async_api import Page, Error as PlaywrightError
from bs4 import BeautifulSoup, NavigableString, Comment
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse
import time
import json
import base64
import sqlite3
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
load_dotenv()

# Global variables (assuming these will be available from your main MCP setup)
# global page  # This should be available from your browser session setup

DB_NAME = os.getenv("DATABASE_AUTH_AGENT_URL")
FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(FERNET_KEY)

# All the existing global helper functions remain the same
def init_database():
    """Initialize the database with required tables if they don't exist."""
    try:
        conn = sqlite3.connect(DB_NAME)
    except sqlite3.Error as e:
        raise RuntimeError(f"❌ Could not connect to database: {e}")
    cursor = conn.cursor()
    
    # Create credentials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT UNIQUE NOT NULL,
            username TEXT,
            password TEXT,
            email TEXT,
            selectors TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create tokens table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT UNIQUE NOT NULL,
            token TEXT NOT NULL,
            exp REAL,
            storage_type TEXT DEFAULT 'localStorage',
            key_name TEXT DEFAULT 'token',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    return f"[init_database] Database initialized at: {DB_NAME}"

def get_connection():
    """Get database connection and ensure database is initialized."""
    if not os.path.exists(DB_NAME):
        init_database()
    
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        init_database()
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

def hostname_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or parsed.netloc or url

def verify_auth(page: Page) -> bool:
    """
    Try to confirm that the current page is authenticated.
    """
    try:
        res = page.evaluate("""
            () => fetch('/api/user', { credentials: 'same-origin' })
                  .then(r => r.ok ? r.json() : { __status: r.status })
                  .catch(e => ({ __error: String(e) }))
        """)
        if isinstance(res, dict):
            if res.get("__error") is not None:
                return False
            if res.get("__status") == 401:
                return False
            if res.get("user") or res.get("email") or res.get("username") or res.get("bio"):
                return True
            if any(k for k in res.keys() if not k.startswith("__")):
                return True
        snapshot = page.evaluate("() => Object.keys(localStorage).length")
        if isinstance(snapshot, int) and snapshot > 0:
            return True
    except Exception as e:
        pass
    return False

def get_token(site_name: str) -> Optional[Dict[str, Optional[str]]]:
    """Return dict with token, exp, storage_type, key_name or None."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT token, exp, storage_type, key_name FROM tokens WHERE site_name = ?", (site_name,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "token": row[0],
            "exp": row[1],
            "storage_type": row[2],
            "key_name": row[3]
        }
    except Exception as e:
        return None

def inject_token_as_cookie(page: Page, url: str, cookie_name: str, token: str) -> bool:
    try:
        page.context.add_cookies([{
            'name': cookie_name,
            'value': token,
            'url': f"{urlparse(url).scheme}://{urlparse(url).hostname}",
            'path': '/',
            'httpOnly': False,
            'sameSite': 'Lax'
        }])
        page.goto(url)
        return verify_auth(page)
    except Exception as e:
        return False
    
def inject_token_to_localstorage(page: Page, url: str, key_name: str, token: str) -> bool:
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.evaluate(
            """(data) => {
                localStorage.setItem(data.key, data.token);
            }""",
            {"key": key_name, "token": token}
        )
        page.reload()
        page.wait_for_timeout(700)
        return verify_auth(page)
    except Exception as e:
        return False

def get_credentials(site_name: str) -> Optional[Dict[str, Optional[str]]]:
    """Return dict with keys username, password, email, selectors or None if not found."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, password, email, selectors FROM credentials WHERE site_name = ?", (site_name,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return None

        selectors = None
        if row[3]:
            try:
                selectors = json.loads(row[3])
            except Exception:
                selectors = None

        return {
            "username": row[0],
            "password": row[1],
            "email": row[2],
            "selectors": selectors
        }
    except Exception as e:
        return None

def save_selectors(site_name: str, selectors: dict):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM credentials WHERE site_name = ?", (site_name,))
        if cur.fetchone():
            cur.execute("UPDATE credentials SET selectors = ?, updated_at = CURRENT_TIMESTAMP WHERE site_name = ?", 
                       (json.dumps(selectors), site_name))
        else:
            cur.execute("INSERT INTO credentials (site_name, selectors) VALUES (?, ?)", 
                       (site_name, json.dumps(selectors)))
        conn.commit()
        conn.close()
    except Exception as e:
        return f"[save_selectors] Error: {e}"

def decode_jwt_exp(jwt_token: str) -> Optional[float]:
    try:
        payload_b64 = jwt_token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        exp = payload.get("exp")
        if exp:
            return float(exp)
    except Exception:
        return None
    return None

def save_credentials(site_name: str, username: Optional[str], password: Optional[str], email: Optional[str] = None, selectors: Optional[dict] = None):
    """Insert or update credentials for a site."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        sel_json = json.dumps(selectors) if selectors is not None else None

        cur.execute("SELECT id FROM credentials WHERE site_name = ?", (site_name,))
        row = cur.fetchone()

        if row:
            cur.execute(
                "UPDATE credentials SET username = ?, password = ?, email = ?, selectors = ?, updated_at = CURRENT_TIMESTAMP WHERE site_name = ?",
                (username, password, email, sel_json, site_name)
            )
        else:
            cur.execute(
                "INSERT INTO credentials (site_name, username, password, email, selectors) VALUES (?, ?, ?, ?, ?)",
                (site_name, username, password, email, sel_json)
            )

        conn.commit()
        conn.close()
    except Exception as e:
        return f"[save_credentials] Error: {e}"

def save_token(site_name: str, token: str, exp: Optional[float], storage_type: Optional[str] = None, key_name: Optional[str] = None):
    """Insert or update token for a site."""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id FROM tokens WHERE site_name = ?", (site_name,))
        if cur.fetchone():
            cur.execute(
                "UPDATE tokens SET token = ?, exp = ?, storage_type = ?, key_name = ?, updated_at = CURRENT_TIMESTAMP WHERE site_name = ?",
                (token, exp, storage_type, key_name, site_name)
            )
        else:
            cur.execute(
                "INSERT INTO tokens (site_name, token, exp, storage_type, key_name) VALUES (?, ?, ?, ?, ?)",
                (site_name, token, exp, storage_type, key_name)
            )
        conn.commit()
        conn.close()
    except Exception as e:
        return f"[save_token] Error: {e}"

# Helper functions extracted from class methods
def find_selector_helper(html: str, pattern: str, fallback_type: str = None, fallback_button: bool = False):
    """Helper function to find selectors from HTML patterns."""
    match = re.search(pattern, html, re.IGNORECASE)
    if match:
        attr_value = match.group().split("=")[-1].strip('"').strip("'")
        if "id=" in match.group().lower():
            return f"#{attr_value}"
        else:
            return f"[name='{attr_value}']"

    if fallback_type:
        if re.search(f'type=["\']{fallback_type}["\']', html, re.IGNORECASE):
            return f"input[type='{fallback_type}']"

    if fallback_button:
        if re.search(r"<button[^>]*>", html, re.IGNORECASE):
            return "button"
        if re.search(r"type=['\"]submit['\"]", html, re.IGNORECASE):
            return "button[type='submit']"

    return None

def find_jwt_anywhere_helper(page: Page):
    """Helper function to find JWT tokens anywhere on the page."""
    jwt_pattern = re.compile(r"eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
    found_tokens = []

    def handle_response(response):
        try:
            body = response.text()
            match = jwt_pattern.search(body)
            if match:
                token = match.group()
                found_tokens.append((f"network:{response.url}", token))
        except:
            pass

    page.on("response", handle_response)
    time.sleep(2)

    # localStorage
    try:
        storage_items = page.evaluate("""() => {
            let items = {};
            for (let i = 0; i < localStorage.length; i++) {
                let key = localStorage.key(i);
                items[`localStorage:${key}`] = localStorage.getItem(key);
            }
            return items;
        }""")
        for key, value in storage_items.items():
            if value and jwt_pattern.search(value):
                found_tokens.append((key, jwt_pattern.search(value).group()))
    except:
        pass

    # sessionStorage
    try:
        session_items = page.evaluate("""() => {
            let items = {};
            for (let i = 0; i < sessionStorage.length; i++) {
                let key = sessionStorage.key(i);
                items[`sessionStorage:${key}`] = sessionStorage.getItem(key);
            }
            return items;
        }""")
        for key, value in session_items.items():
            if value and jwt_pattern.search(value):
                found_tokens.append((key, jwt_pattern.search(value).group()))
    except:
        pass

    # cookies
    try:
        cookies = page.context.cookies()
        for c in cookies:
            if jwt_pattern.search(c['value']):
                found_tokens.append((f"cookie:{c['name']}", jwt_pattern.search(c['value']).group()))
    except:
        pass

    if found_tokens:
        seen = set()
        for source, token in found_tokens:
            if token not in seen:
                seen.add(token)
                if source.startswith('localStorage:'):
                    key_name = source.split(':', 1)[1]
                    return token, f"localStorage:{key_name}"
                if source.startswith('sessionStorage:'):
                    key_name = source.split(':', 1)[1]
                    return token, f"sessionStorage:{key_name}"
                if source.startswith('cookie:') or source.startswith('network:'):
                    return token, source
    return None, None

# MCP Tools
@mcp.tool()
def extract_selectors(parsed_html: str) -> dict:
    """Extracts selectors for all possible login-related fields from parsed HTML."""
    selectors = {
        "username_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:username|user|login)[^"\s>]*"?', fallback_type="text"),
        "email_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:email)[^"\s>]*"?', fallback_type="email"),
        "password_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:password|pass)[^"\s>]*"?', fallback_type="password"),
        "otp_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:otp|code)[^"\s>]*"?', fallback_type="number"),
        "submit_selector": find_selector_helper(parsed_html, r'(?:id|name)="?(?:submit|login|Sign in)[^"\s>]*"?', fallback_button=True)
    }

    if not selectors["submit_selector"]:
        selectors["submit_selector"] = "button[type='submit'], text=Login, text=Sign in"

    return selectors

@mcp.tool()
def playwright_login(url: str, credentials: dict, selectors: dict) -> bool:
    """Logs into a site using Playwright by filling only available fields."""
    global page
    try:
        page.goto(url)

        if selectors.get("username_selector") and credentials.get("username"):
            username = fernet.decrypt(credentials["username"].encode()).decode()
            page.fill(selectors["username_selector"], username)

        # email
        if selectors.get("email_selector") and credentials.get("email"):
            email = fernet.decrypt(credentials["email"].encode()).decode()
            page.fill(selectors["email_selector"], email)

        # password
        if selectors.get("password_selector") and credentials.get("password"):
            password = fernet.decrypt(credentials["password"].encode()).decode()
            page.fill(selectors["password_selector"], password)

        # otp
        if selectors.get("otp_selector") and credentials.get("otp"):
            otp = fernet.decrypt(credentials["otp"].encode()).decode()
            page.fill(selectors["otp_selector"], otp)

        if selectors.get("submit_selector"):
            try:
                page.click("button[type='submit']")
            except:
                page.press("input[name='password']", "Enter")
        else:
            page.keyboard.press("Enter")
            
        # Small wait for navigation/requests
        page.wait_for_timeout(4000)
        return True
    except Exception as e:
        return False

@mcp.tool()
def smart_login(url: str, parsed_html: str) -> str:
    """Main smart login tool - tries token first, then credentials, with detailed error reporting."""
    global page
    try:
        # Initialize database
        init_database()
        site_key = hostname_from_url(url)
        
        # STEP 1: Try existing token
        try:
            token_record = get_token(site_key)
            if token_record:
                token = token_record.get('token')
                exp = token_record.get('exp')
                key_name = token_record.get('key_name') or 'token'
                storage_type = token_record.get('storage_type') or 'localStorage'

                if exp and time.time() < float(exp):
                    injected_ok = False
                    if storage_type == 'cookie':
                        injected_ok = inject_token_as_cookie(page, url, key_name, token)
                    else:
                        injected_ok = inject_token_to_localstorage(page, url, key_name, token)

                    if injected_ok:
                        return f"✅ Login successful using stored token for {site_key} (source: {storage_type})"
        except Exception as e:
            # Token method failed, continue to credentials
            pass

        # STEP 2: Extract selectors if needed
        try:
            creds = get_credentials(site_key)
            selectors = None
            if creds and creds.get('selectors'):
                selectors = creds.get('selectors')
            
            if not selectors:
                selectors = extract_selectors_internal(parsed_html)
                save_selectors(site_key, selectors)
        except Exception as e:
            return f"❌ Error extracting selectors: {e}"

        # STEP 3: Try credential-based login
        try:
            if creds and (creds.get('username') or creds.get('email')) and creds.get('password'):
                credentials_payload = {
                    'username': creds.get('username'),
                    'email': creds.get('email'),
                    'password': creds.get('password')
                }

                success = playwright_login_internal(page, url, credentials_payload, selectors)
                
                if success:
                    # Try to find and save new token
                    try:
                        jwt_token, found_source = find_jwt_anywhere_helper(page)
                        if jwt_token:
                            exp_time = decode_jwt_exp(jwt_token) or (time.time() + 3600)
                            save_token(site_key, jwt_token, exp_time, storage_type='localStorage', key_name='token')
                            return f"✅ Login successful using credentials for {site_key}. JWT token found and saved (source: {found_source})"
                        else:
                            return f"✅ Login successful using credentials for {site_key}. No JWT token found but login completed."
                    except Exception as e:
                        return f"✅ Login successful using credentials for {site_key}. Error searching for JWT: {e}"
                else:
                    return f"❌ Login failed for {site_key} - form submission completed but authentication unsuccessful"
            else:
                return f"❌ No stored credentials available for {site_key}. Please store credentials first."
                
        except Exception as e:
            return f"❌ Error during credential login for {site_key}: {e}"
            
    except Exception as e:
        return f"❌ Smart login failed for {site_key}: {e}"