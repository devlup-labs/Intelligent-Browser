"""
Auth agent - the only component allowed to read plaintext credentials.
All other code sees only platform names and login status.
"""
from __future__ import annotations

from playwright.async_api import Page

from ..utils.logger import get_logger
from .strategies import STRATEGY_REGISTRY, LoginFailedError, MFARequiredError
from .vault import get_credential

logger = get_logger(__name__)


async def authenticate(
    platform: str,
    page: Page,
    mfa_callback=None,
) -> dict:
    """
    Log in to `platform` using stored credentials.

    Args:
        platform:     e.g. "linkedin", "gmail"
        page:         Active Playwright Page (from BrowserManager)
        mfa_callback: Optional async callable(platform, prompt) -> str
                      that resolves an MFA code from the user (via WebSocket).

    Returns:
        {"status": "ok", "platform": platform}
        {"status": "error", "platform": platform, "message": "..."}
        {"status": "mfa_required", "platform": platform, "prompt": "..."}
        {"status": "no_credentials", "platform": platform}
        {"status": "unsupported", "platform": platform}
    """
    platform = platform.lower()

    # 1. Check credentials exist - do this before touching the browser
    credential = get_credential(platform)
    if credential is None:
        logger.warning("No credentials stored for platform: %s", platform)
        return {"status": "no_credentials", "platform": platform}

    # 2. Check strategy exists
    strategy = STRATEGY_REGISTRY.get(platform)
    if strategy is None:
        logger.warning("No login strategy for platform: %s", platform)
        return {"status": "unsupported", "platform": platform}

    username, password = credential

    try:
        await strategy.login(page, username, password)
        logger.info("Successfully authenticated to %s", platform)
        return {"status": "ok", "platform": platform}

    except MFARequiredError as e:
        logger.info("MFA required for %s", platform)
        if mfa_callback is not None:
            await mfa_callback(e.platform, e.prompt)
        return {"status": "mfa_required", "platform": platform, "prompt": e.prompt}

    except LoginFailedError as e:
        logger.error("Login failed for %s: %s", platform, str(e))
        return {"status": "error", "platform": platform, "message": str(e)}

    except Exception:
        logger.exception("Unexpected error during login to %s", platform)
        return {"status": "error", "platform": platform, "message": "Unexpected login error"}

    finally:
        # Explicitly delete local references to credentials
        del username, password
        del credential
