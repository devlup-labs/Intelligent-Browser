"""
Credential vault - AES-GCM encrypted, local disk only.
Passwords are NEVER logged, returned via API, or placed in AgentState.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------
# The key is derived from a stable per-machine secret written once to disk.
# This is NOT high-security HSM-grade protection; it is the same security
# model as a password manager that auto-unlocks on the owner's machine.
# If the threat model requires a user master-password, replace _load_key()
# accordingly.

def _master_secret_path() -> Path:
    return Path(settings.vault_store_path).parent / ".vault_secret"


def _load_key() -> bytes:
    """Return a 32-byte AES key, creating it on first run."""
    secret_path = _master_secret_path()
    secret_path.parent.mkdir(parents=True, exist_ok=True)
    if secret_path.exists():
        raw = secret_path.read_bytes()
    else:
        raw = os.urandom(32)
        secret_path.write_bytes(raw)
        secret_path.chmod(0o600)
    # Stretch via SHA-256 (already 32 bytes but keeps the interface stable
    # if we switch to a passphrase-derived key later)
    return hashlib.sha256(raw).digest()


# ---------------------------------------------------------------------------
# Vault read / write
# ---------------------------------------------------------------------------

def _vault_path() -> Path:
    return Path(settings.vault_store_path)


def _read_vault() -> dict[str, dict]:
    """Return decrypted vault contents as {platform: {username, password}}."""
    path = _vault_path()
    if not path.exists():
        return {}
    try:
        blob = path.read_bytes()
        # Format: 12-byte nonce || ciphertext
        nonce, ciphertext = blob[:12], blob[12:]
        key = _load_key()
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        return json.loads(plaintext)
    except Exception:
        logger.error("Failed to decrypt vault - it may be corrupted or the key changed.")
        return {}


def _write_vault(data: dict[str, dict]) -> None:
    """Encrypt and write vault contents to disk."""
    path = _vault_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    key = _load_key()
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, json.dumps(data).encode(), None)
    path.write_bytes(nonce + ciphertext)
    path.chmod(0o600)


# ---------------------------------------------------------------------------
# Public API (used by routes.py and agent.py)
# ---------------------------------------------------------------------------

def save_credential(platform: str, username: str, password: str) -> None:
    """Upsert a credential. Password is encrypted at rest immediately."""
    vault = _read_vault()
    vault[platform.lower()] = {"username": username, "password": password}
    _write_vault(vault)
    logger.info("Credential saved for platform: %s", platform)


def delete_credential(platform: str) -> bool:
    """Remove a credential. Returns True if it existed."""
    vault = _read_vault()
    existed = platform.lower() in vault
    if existed:
        vault.pop(platform.lower())
        _write_vault(vault)
        logger.info("Credential deleted for platform: %s", platform)
    return existed


def list_platforms() -> list[str]:
    """Return platform names only - NEVER returns usernames or passwords."""
    return list(_read_vault().keys())


def get_credential(platform: str) -> Optional[tuple[str, str]]:
    """
    Return (username, password) for internal use by the auth agent ONLY.
    This function must NEVER be called from any code path that touches
    AgentState, LLM prompts, or API responses.
    """
    vault = _read_vault()
    entry = vault.get(platform.lower())
    if entry is None:
        return None
    return entry["username"], entry["password"]
