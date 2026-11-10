import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_admin(x_admin_key: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Admin-Key")
