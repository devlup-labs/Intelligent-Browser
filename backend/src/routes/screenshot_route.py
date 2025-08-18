from pathlib import Path
from fastapi import APIRouter

screenshot_dir = Path(__file__).resolve().parent.parent.parent.parent/"frontend"/"public"/"screenshots"
screenshot_dir.mkdir(parents=True,exist_ok=True)

ss_router=APIRouter()


