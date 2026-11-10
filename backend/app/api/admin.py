import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.connectors.registry import get_connector_class
from app.database import get_db
from app.models import Company, IngestionRun, Job, JobStatus, Source
from app.schemas import IngestionRunOut, SourceCreate, SourceOut
from app.workers.tasks import ingest_source

router = APIRouter(prefix="/api/v1/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _get_source(db: Session, source_id: uuid.UUID) -> Source:
    source = db.get(Source, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)) -> Source:
    try:
        cls = get_connector_class(payload.connector)
        cls.validate_config(payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if db.scalar(select(Source).where(Source.name == payload.name)):
        raise HTTPException(status_code=409, detail="A source with this name already exists")
    source = Source(
        name=payload.name, platform_type=cls.platform_type, connector=cls.key,
        connector_type=cls.connector_type, base_url=cls.build_base_url(payload.config),
        config=payload.config, schedule_minutes=payload.schedule_minutes,
    )
    db.add(source)
    db.commit()
    return source


@router.post("/sources/{source_id}/run", status_code=202)
def run_source_now(source_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    source = _get_source(db, source_id)
    task = ingest_source.delay(str(source.id), "manual")
    return {"queued": True, "task_id": task.id}


@router.post("/sources/{source_id}/enable", response_model=SourceOut)
def enable_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> Source:
    source = _get_source(db, source_id)
    source.is_active = True
    db.commit()
    return source


@router.post("/sources/{source_id}/disable", response_model=SourceOut)
def disable_source(source_id: uuid.UUID, db: Session = Depends(get_db)) -> Source:
    source = _get_source(db, source_id)
    source.is_active = False
    db.commit()
    return source


@router.get("/ingestion-runs", response_model=list[IngestionRunOut])
def list_runs(source_id: uuid.UUID | None = None, limit: int = 50, db: Session = Depends(get_db)) -> list[IngestionRun]:
    stmt = select(IngestionRun).order_by(IngestionRun.started_at.desc()).limit(min(limit, 200))
    if source_id:
        stmt = stmt.where(IngestionRun.source_id == source_id)
    return list(db.scalars(stmt))


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    by_status = dict(db.execute(select(Job.status, func.count()).group_by(Job.status)).all())
    return {
        "sources_total": db.scalar(select(func.count()).select_from(Source)),
        "sources_active": db.scalar(select(func.count()).select_from(Source).where(Source.is_active.is_(True))),
        "sources_failing": db.scalar(
            select(func.count()).select_from(Source).where(
                Source.last_error_at.is_not(None),
                (Source.last_success_at.is_(None)) | (Source.last_error_at > Source.last_success_at),
            )
        ),
        "companies_total": db.scalar(select(func.count()).select_from(Company)),
        "jobs_by_status": by_status,
        "jobs_active": by_status.get(JobStatus.ACTIVE, 0),
    }
