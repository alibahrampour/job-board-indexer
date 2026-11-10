import logging
from datetime import timedelta

import redis
from redis.exceptions import LockError
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Source
from app.services.ingestion import run_source, utcnow
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)
_redis = redis.Redis.from_url(settings.redis_url)


@celery_app.task(name="ingest_source")
def ingest_source(source_id: str, trigger: str = "schedule") -> dict:
    # One run per source at a time, even with several workers.
    lock = _redis.lock(f"lock:ingest:{source_id}", timeout=1800)
    if not lock.acquire(blocking=False):
        return {"status": "SKIPPED", "reason": "already running"}
    try:
        return run_source(source_id, trigger)
    finally:
        try:
            lock.release()
        except LockError:
            pass


@celery_app.task(name="enqueue_due_sources")
def enqueue_due_sources() -> int:
    now = utcnow()
    count = 0
    with SessionLocal() as db:
        sources = db.scalars(select(Source).where(Source.is_active.is_(True))).all()
        for s in sources:
            due = s.last_run_at is None or s.last_run_at <= now - timedelta(minutes=s.schedule_minutes)
            if due:
                s.last_run_at = now  # prevents re-enqueueing while the task waits in the queue
                ingest_source.delay(str(s.id), "schedule")
                count += 1
        db.commit()
    log.info("enqueued %d sources", count)
    return count
