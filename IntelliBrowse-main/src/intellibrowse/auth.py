"""
Google OAuth token verification helpers.
"""

from __future__ import annotations

import anyio
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token as google_id_token

from intellibrowse.config import settings


def _verify_token_sync(token: str) -> dict:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_ID not configured",
        )

    try:
        return google_id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid Google ID token",
        ) from exc


async def verify_google_id_token(token: str) -> dict:
    """Verify Google ID token and return its claims."""
    return await anyio.to_thread.run_sync(_verify_token_sync, token)


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing Authorization header",
        )

    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid Authorization header",
        )

    token = authorization[len(prefix):].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
        )

    return token
