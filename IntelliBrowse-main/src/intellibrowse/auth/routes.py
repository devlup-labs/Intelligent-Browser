"""
FastAPI router for the credential vault.
Passwords are accepted as input but NEVER returned in any response.
These routes should only be reachable from localhost in production.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, SecretStr

from ..utils.logger import get_logger
from .vault import delete_credential, list_platforms, save_credential

logger = get_logger(__name__)
router = APIRouter(prefix="/vault", tags=["auth-vault"])


class SaveCredentialRequest(BaseModel):
    platform: str
    username: str
    password: SecretStr


class PlatformsResponse(BaseModel):
    platforms: list[str]


class StatusResponse(BaseModel):
    status: str
    platform: str


@router.get("/platforms", response_model=PlatformsResponse)
async def get_platforms() -> PlatformsResponse:
    """Return list of platform names for which credentials are stored. No passwords."""
    return PlatformsResponse(platforms=list_platforms())


@router.post("/credentials", response_model=StatusResponse, status_code=status.HTTP_201_CREATED)
async def upsert_credential(req: SaveCredentialRequest) -> StatusResponse:
    """Save or update a credential. Password is encrypted on disk immediately."""
    try:
        save_credential(req.platform, req.username, req.password.get_secret_value())
        return StatusResponse(status="saved", platform=req.platform)
    except Exception as exc:
        logger.exception("Failed to save credential for %s", req.platform)
        raise HTTPException(status_code=500, detail="Failed to save credential") from exc


@router.delete("/credentials/{platform}", response_model=StatusResponse)
async def remove_credential(platform: str) -> StatusResponse:
    """Delete a stored credential."""
    existed = delete_credential(platform)
    if not existed:
        raise HTTPException(status_code=404, detail=f"No credential found for '{platform}'")
    return StatusResponse(status="deleted", platform=platform)
