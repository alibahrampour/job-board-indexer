from celery import Celery

from app.config import settings

celery_app = Celery(
    "jobindexer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    timezone="UTC",
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=1800,
    beat_schedule={
        "enqueue-due-sources": {"task": "enqueue_due_sources", "schedule": 300.0},
    },
)
