import sqlite3
import json
import time
from typing import Optional, Tuple, Dict

DB_NAME = "database.db"

# -------------------------
# Low-level helpers
# -------------------------
def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------
# Init
# -------------------------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # credentials table: stores site-specific credentials and optional selectors
    cur.execute('''
        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT NOT NULL UNIQUE,
            username TEXT,
            email TEXT,
            password TEXT,
            selectors TEXT
        )
    ''')

    # tokens table: stores token, expiry, storage type and key name
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_name TEXT NOT NULL UNIQUE,
            token TEXT NOT NULL,
            exp REAL,
            storage_type TEXT,
            key_name TEXT
        )
    ''')

    conn.commit()
    conn.close()

# -------------------------
# Credentials API
# -------------------------
def save_credentials(site_name: str, username: Optional[str], password: Optional[str], email: Optional[str] = None, selectors: Optional[dict] = None):
    """Insert or update credentials for a site. selectors is a dict (will be JSON-encoded)."""
    conn = get_connection()
    cur = conn.cursor()

    sel_json = json.dumps(selectors) if selectors is not None else None

    cur.execute("SELECT id FROM credentials WHERE site_name = ?", (site_name,))
    row = cur.fetchone()

    if row:
        cur.execute(
            "UPDATE credentials SET username = ?, password = ?, email = ?, selectors = ? WHERE site_name = ?",
            (username, password, email, sel_json, site_name)
        )
    else:
        cur.execute(
            "INSERT INTO credentials (site_name, username, password, email, selectors) VALUES (?, ?, ?, ?, ?)",
            (site_name, username, password, email, sel_json)
        )

    conn.commit()
    conn.close()


def get_credentials(site_name: str) -> Optional[Dict[str, Optional[str]]]:
    """Return dict with keys username, password, email, selectors (selectors is a dict or None) or None if not found."""
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

# -------------------------
# Selectors helpers (convenience)
# -------------------------
def save_selectors(site_name: str, selectors: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM credentials WHERE site_name = ?", (site_name,))
    if cur.fetchone():
        cur.execute("UPDATE credentials SET selectors = ? WHERE site_name = ?", (json.dumps(selectors), site_name))
    else:
        cur.execute("INSERT INTO credentials (site_name, selectors) VALUES (?, ?)", (site_name, json.dumps(selectors)))
    conn.commit()
    conn.close()

def get_selectors(site_name: str) -> Optional[dict]:
    creds = get_credentials(site_name)
    if not creds:
        return None
    return creds.get("selectors")

# -------------------------
# Token API
# -------------------------
def save_token(site_name: str, token: str, exp: Optional[float], storage_type: Optional[str] = None, key_name: Optional[str] = None):
    """Insert or update token for a site. exp is unix timestamp (float)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id FROM tokens WHERE site_name = ?", (site_name,))
    if cur.fetchone():
        cur.execute(
            "UPDATE tokens SET token = ?, exp = ?, storage_type = ?, key_name = ? WHERE site_name = ?",
            (token, exp, storage_type, key_name, site_name)
        )
    else:
        cur.execute(
            "INSERT INTO tokens (site_name, token, exp, storage_type, key_name) VALUES (?, ?, ?, ?, ?)",
            (site_name, token, exp, storage_type, key_name)
        )
    conn.commit()
    conn.close()


def get_token(site_name: str) -> Optional[Dict[str, Optional[str]]]:
    """Return dict with token, exp, storage_type, key_name or None."""
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


def invalidate_token(site_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM tokens WHERE site_name = ?", (site_name,))
    conn.commit()
    conn.close()

# Initialize DB when imported
init_db()