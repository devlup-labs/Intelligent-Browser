"""
Long-term memory — simple JSON file that stores learned patterns per domain.

Things like "always dismiss the popup on this site first" persist across tasks.
Injected into the system prompt when the current URL's domain matches.

Storage: memory_store/domains.json
Format:
{
    "github.com": {
        "patterns": ["dismiss cookie banner first", "use tab navigation for repo list"],
        "last_updated": "2025-01-15T10:30:00"
    }
}
"""

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from intellibrowse.config import settings
from intellibrowse.utils.logger import get_logger

logger = get_logger(__name__)


def _get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # Strip www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def _load_store() -> dict:
    """Load the memory store from disk."""
    path = settings.memory_store_path
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("failed to load memory store: %s", e)
        return {}


def _save_store(store: dict):
    """Write the memory store to disk."""
    path = settings.memory_store_path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(store, f, indent=2)


def get_domain_hints(url: str) -> list[str]:
    """
    Get learned patterns for the current URL's domain.
    Returns an empty list if no patterns exist.
    """
    domain = _get_domain(url)
    if not domain:
        return []

    store = _load_store()
    entry = store.get(domain, {})
    patterns = entry.get("patterns", [])

    if patterns:
        logger.info("found %d domain hints for %s", len(patterns), domain)

    return patterns


def save_pattern(url: str, pattern: str):
    """Save a learned pattern for a domain."""
    domain = _get_domain(url)
    if not domain:
        return

    store = _load_store()

    if domain not in store:
        store[domain] = {"patterns": [], "last_updated": ""}

    # Avoid duplicates
    if pattern not in store[domain]["patterns"]:
        store[domain]["patterns"].append(pattern)
        store[domain]["last_updated"] = datetime.now(timezone.utc).isoformat()
        _save_store(store)
        logger.info("saved pattern for %s: %s", domain, pattern)
