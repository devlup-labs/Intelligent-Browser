from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from playwright.async_api import Page, Error as PlaywrightError
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

load_dotenv()

DB_NAME = os.getenv("DATABASE_AUTH_AGENT_URL", "auth_agent.db")

def init_database():
    """Initialize the database with required tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
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
    print(f"[init_database] Database initialized at: {DB_NAME}")

def get_connection():
    """Get database connection and ensure database is initialized."""
    # Ensure database exists and is initialized
    if not os.path.exists(DB_NAME):
        print(f"[get_connection] Database file doesn't exist, creating: {DB_NAME}")
        init_database()
    
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"[get_connection] Database connection error: {e}")
        # Try to initialize database if connection fails
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
    - Primary: call /api/user (Conduit pattern). If it returns a user object -> authenticated.
    - Fallback: check that some token-like localStorage key exists.
    Returns True if we believe session is authenticated, else False.
    """
    try:
        # Try the known Conduit endpoint to confirm server accepts the session
        res = page.evaluate("""
            () => fetch('/api/user', { credentials: 'same-origin' })
                  .then(r => r.ok ? r.json() : { __status: r.status })
                  .catch(e => ({ __error: String(e) }))
        """)
        # res will be a Python object deserialized from JSON
        if isinstance(res, dict):
            if res.get("__error") is not None:
                return False
            if res.get("__status") == 401:
                return False
            # likely a user object if not status/error
            if res.get("user") or res.get("email") or res.get("username") or res.get("bio"):
                return True
            # some APIs return the object itself
            # if it contains at least one key other than our markers, consider authenticated
            if any(k for k in res.keys() if not k.startswith("__")):
                return True
        # Fallback: check localStorage non-empty
        snapshot = page.evaluate("() => Object.keys(localStorage).length")
        if isinstance(snapshot, int) and snapshot > 0:
            return True
    except Exception as e:
        print(f"[verify_auth] Error: {e}")
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
        print(f"[get_token] Error: {e}")
        return None

def inject_token_as_cookie(page: Page, url: str, cookie_name: str, token: str) -> bool:
    try:
        page.context.add_cookies([{
            'name': cookie_name,
            'value': token,
            'url': f"{urlparse(url).scheme}://{urlparse(url).hostname}",
            # more reliable than domain-only
            'path': '/',
            'httpOnly': False,
            'sameSite': 'Lax'
        }])
        page.goto(url)
        return verify_auth(page)
    except Exception as e:
        print(f"[inject_token_as_cookie] Error: {e}")
        return False
    
def inject_token_to_localstorage(page: Page, url: str, key_name: str, token: str) -> bool:
    try:
        # navigate first so same-origin policies allow setting localStorage
        page.goto(url, wait_until="domcontentloaded")

        # use evaluate with args to avoid JS quoting issues
        page.evaluate(
            """(data) => {
                localStorage.setItem(data.key, data.token);
            }""",
            {"key": key_name, "token": token}
        )

        # reload so app bootstrapping can read it
        page.reload()
        page.wait_for_timeout(700)

        # verify auth (see helper below)
        return verify_auth(page)
    except Exception as e:
        print(f"[inject_token_to_localstorage] Error: {e}")
        return False

def get_credentials(site_name: str) -> Optional[Dict[str, Optional[str]]]:
    """Return dict with keys username, password, email, selectors (selectors is a dict or None) or None if not found."""
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
        print(f"[get_credentials] Error: {e}")
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
        print(f"[save_selectors] Error: {e}")

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
    """Insert or update credentials for a site. selectors is a dict (will be JSON-encoded)."""
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
        print(f"[save_credentials] Error: {e}")

def save_token(site_name: str, token: str, exp: Optional[float], storage_type: Optional[str] = None, key_name: Optional[str] = None):
    """Insert or update token for a site. exp is unix timestamp (float)."""
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
        print(f"[save_token] Error: {e}")

class SelectorExtractorInput(BaseModel):
    parsed_html: str = Field(..., description="Parsed HTML with only interactive elements")

class SelectorExtractorTool(BaseTool):
    name: str = "selector_extractor"
    description: str = "Extracts selectors for all possible login-related fields from parsed HTML."
    args_schema: type[BaseModel] = SelectorExtractorInput

    def _run(self, parsed_html: str) -> dict:
        selectors = {
            "username_selector": self._find_selector(parsed_html, r'(?:id|name)="?(?:username|user|login)[^"\s>]*"?', fallback_type="text"),
            "email_selector": self._find_selector(parsed_html, r'(?:id|name)="?(?:email)[^"\s>]*"?', fallback_type="email"),
            "password_selector": self._find_selector(parsed_html, r'(?:id|name)="?(?:password|pass)[^"\s>]*"?', fallback_type="password"),
            "otp_selector": self._find_selector(parsed_html, r'(?:id|name)="?(?:otp|code)[^"\s>]*"?', fallback_type="number"),
            "submit_selector": self._find_selector(parsed_html, r'(?:id|name)="?(?:submit|login|Sign in)[^"\s>]*"?', fallback_button=True)
        }

        if not selectors["submit_selector"]:
            selectors["submit_selector"] = "button[type='submit'], text=Login, text=Sign in"

        return selectors

    def _find_selector(self, html: str, pattern: str, fallback_type: str = None, fallback_button: bool = False):
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

# -------------------------
# Playwright Login Tool
# -------------------------

class PlaywrightLoginInput(BaseModel):
    url: str = Field(..., description="URL to navigate to for login")
    credentials: dict = Field(..., description="Dictionary containing login credentials")
    selectors: dict = Field(..., description="Dictionary containing CSS selectors for form elements")

class PlaywrightLoginTool(BaseTool):
    name: str = "playwright_login"
    description: str = "Logs into a site using Playwright by filling only available fields."
    args_schema: type[BaseModel] = PlaywrightLoginInput
    page: Page = Field(exclude=True)  # Exclude from serialization
    
    def __init__(self, name: str, description: str, page: Page):
        super().__init__(name=name, description=description, page=page)

    def _run(self, url: str, credentials: dict, selectors: dict):
        try:
            self.page.goto(url)

            if selectors.get("username_selector") and credentials.get("username"):
                self.page.fill(selectors["username_selector"], credentials["username"])
            if selectors.get("email_selector") and credentials.get("email"):
                self.page.fill(selectors["email_selector"], credentials["email"])
            if selectors.get("password_selector") and credentials.get("password"):
                self.page.fill(selectors["password_selector"], credentials["password"])
            if selectors.get("otp_selector") and credentials.get("otp"):
                self.page.fill(selectors["otp_selector"], credentials["otp"])

            if selectors.get("submit_selector"):
                self.page.click(selectors["submit_selector"])
            else:
                self.page.keyboard.press("Enter")
                
            # Small wait for navigation/requests
            self.page.wait_for_timeout(4000)
            return True
        except Exception as e:
            print(f"[PlaywrightLoginTool] Error: {e}")
            return False

# -------------------------
# SmartLoginTool (3-tier logic)
# -------------------------


class SmartLoginInput(BaseModel):
    url: str = Field(..., description="URL of the site to login to")
    parsed_html: str = Field(..., description="Parsed HTML content of the login page")

class SmartLoginTool(BaseTool):
    name: str = "smart_login"
    description: str = "Logs into a site, reuses stored tokens if valid, or falls back to credentials/user prompt."
    args_schema: type[BaseModel] = SmartLoginInput
    page: Page = Field(exclude=True)  # Exclude from serialization
    
    def __init__(self, name: str, description: str, page: Page):
        super().__init__(name=name, description=description, page=page)

    def _run(self, url: str, parsed_html: str) -> dict:
        try:
            # Initialize database on first run
            init_database()
            
            site_key = hostname_from_url(url)
            print(f"[smart_login] site_key={site_key}")
            
            # 1) Token-first
            token_record = get_token(site_key)
            print(f"[smart_login] token_record={token_record}")
            if token_record:
                token = token_record.get('token')
                exp = token_record.get('exp')
                key_name = token_record.get('key_name') or 'token'
                storage_type = token_record.get('storage_type') or 'localStorage'

                if exp and time.time() < float(exp):
                    print(f"[smart_login] trying to inject token into {storage_type} with key {key_name}")
                    try:
                        injected_ok = False
                        if storage_type == 'cookie':
                            injected_ok = inject_token_as_cookie(self.page, url, key_name, token)
                        else:
                            injected_ok = inject_token_to_localstorage(self.page, url, key_name, token)

                        if injected_ok:
                            print("[smart_login] token injection verified — session authenticated")
                            return {"jwt": token, "source": "db_token"}
                        else:
                            print("[smart_login] token injection did NOT create an authenticated session; falling back")
                    except Exception as e:
                        print(f"[smart_login] token injection error: {e}; falling back to credentials")
                        # continue to credentials path

            # 2) Credentials-second
            creds = get_credentials(site_key)
            selectors = None
            if creds and creds.get('selectors'):
                selectors = creds.get('selectors')

            print("[smart_login] falling back to credential-based login")
            # If selectors not saved, extract them from parsed_html
            if not selectors:
                selectors = SelectorExtractorTool()._run(parsed_html)
                # Save selectors for future
                try:
                    save_selectors(site_key, selectors)
                except Exception:
                    pass

            # If credentials exist in DB, use them
            if creds and (creds.get('username') or creds.get('email')) and creds.get('password'):
                credentials_payload = {
                    'username': creds.get('username'),
                    'email': creds.get('email'),
                    'password': creds.get('password')
                }

                login_tool = PlaywrightLoginTool(name="temp_login", description="temp", page=self.page)
                success = login_tool._run(url=url, credentials=credentials_payload, selectors=selectors)

                if success:
                    jwt_token, found_source = self._find_jwt_anywhere(self.page)
                    if jwt_token:
                        exp_time = decode_jwt_exp(jwt_token) or (time.time() + 3600)
                        save_token(site_key, jwt_token, exp_time, storage_type='localStorage', key_name='token')
                        return {"jwt": jwt_token, "source": found_source}
                    else:
                        return {"result": "login_attempted_but_no_jwt_found"}

            # 3) For now, return message instead of prompting user
            # In production, you might want to implement user prompting differently
            return {"result": "no_stored_credentials_available", "message": "Please provide credentials for this site"}

        except Exception as e:
            print(f"[smart_login] Error: {e}")
            return {"error": str(e), "result": "smart_login_failed"}

    def _find_jwt_anywhere(self, page: Page):
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
                    # also try to infer storage type & key
                    if source.startswith('localStorage:'):
                        key_name = source.split(':', 1)[1]
                        return token, f"localStorage:{key_name}"
                    if source.startswith('sessionStorage:'):
                        key_name = source.split(':', 1)[1]
                        return token, f"sessionStorage:{key_name}"
                    if source.startswith('cookie:') or source.startswith('network:'):
                        return token, source
        return None, None