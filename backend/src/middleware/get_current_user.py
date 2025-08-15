from fastapi import Depends,HTTPException,status
from fastapi.security import OAuth2PasswordBearer
from src.controllers.auth import validate_token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login") # extracts the token from authorization header
async def getCurrentUser(token:str=Depends(oauth2_scheme)):
    payload=validate_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Expired Token"
        )
    return payload #you will get user's username and id;

