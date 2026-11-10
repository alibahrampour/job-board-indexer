import redis
from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.config import settings
from app.database import engine

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        redis.Redis.from_url(settings.redis_url).ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"not ready: {exc}")
    return {"status": "ready"}
