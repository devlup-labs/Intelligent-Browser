import sqlite3
import os
from dotenv import load_dotenv

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
