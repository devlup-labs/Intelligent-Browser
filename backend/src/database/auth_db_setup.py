import sqlite3
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
load_dotenv()

# Read full database url from env
db_url = os.getenv("DATABASE_AUTH_AGENT_URL")
if not db_url:
    raise ValueError("DATABASE_AUTH_AGENT_URL environment variable not set in .env")

# Remove the 'sqlite:///' prefix to get a file path
# Remove sqlite:/// or sqlite://// prefixes to get a clean file path
if db_url.startswith("sqlite:////"):  # absolute path
    db_path = db_url[len("sqlite:////")-1:]  # keep the leading slash
elif db_url.startswith("sqlite:///"):  # relative path
    db_path = db_url[len("sqlite:///"):]
else:
    db_path = db_url  # fallback
  # fallback if not prefixed

fernet_key = os.getenv("FERNET_KEY")

if not fernet_key:
    raise ValueError("FERNET_KEY not set in .env")

fernet = Fernet(fernet_key.encode())

def encrypt(value: str) -> str:
    if value is None:
        return None
    return fernet.encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    if value is None:
        return None
    return fernet.decrypt(value.encode()).decode()

def ensure_db_dir_exists(db_path):
    dir_name = os.path.dirname(db_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

def setup_database():
    ensure_db_dir_exists(db_path)

    if not os.path.exists(db_path):
        print(f"Warning: database file does not exist at expected path {db_path}. A new file will be created.")
    else:
        print(f"Database file found at {db_path}, will connect and update existing file.")

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as e:
        raise RuntimeError(f"❌ Could not connect to database: {e}")

    cursor = conn.cursor()

    # Create tables if they don't exist
    try:
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
    except sqlite3.Error as e:
        conn.close()
        raise RuntimeError(f"❌ Table creation failed: {e}")

    # Upsert Instagram credentials
    try:
        cursor.execute("""
        INSERT OR REPLACE INTO credentials (site_name, username, password, email, selectors)
        VALUES (?, ?, ?, ?, ?)
        """, (
            "www.instagram.com",
            encrypt("Intelli_Browse"),
            encrypt("wiggly.213"),
            None,
            None
        ))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        raise RuntimeError(f"❌ Failed to insert credentials: {e}")

    conn.close()
    print(f"✅ Database updated with Instagram credentials at: {db_path}")


if __name__ == "__main__":
    setup_database()
