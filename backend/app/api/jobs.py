import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.models import Job, JobSource
from app.schemas import JobDetail, JobSourceOut, JobSummary, SearchResponse
from app.services.search_service import search_jobs

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("/search", response_model=SearchResponse)
def search(
    q: str | None = Query(None, description="Free text; supports quotes and -exclusions"),
    location: str | None = Query(None, description="City, country code or free text"),
    remote_type: Literal["REMOTE", "HYBRID", "ONSITE"] | None = None,
    employment_type: str | None = Query(None, description="FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP, TEMPORARY"),
    seniority: str | None = None,
    company: str | None = None,
    posted_within_days: int | None = Query(None, ge=1, le=365),
    sort: Literal["relevance", "newest"] = "relevance",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    total, jobs = search_jobs(
        db, q=q, location=location, remote_type=remote_type, employment_type=employment_type,
        seniority=seniority, company=company, posted_within_days=posted_within_days,
        sort=sort, page=page, page_size=page_size,
    )
    return SearchResponse(
        total=total, page=page, page_size=page_size,
        results=[JobSummary.model_validate(j) for j in jobs],
    )


@router.get("/latest", response_model=SearchResponse)
def latest(page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)) -> SearchResponse:
    total, jobs = search_jobs(db, sort="newest", page=1, page_size=page_size)
    return SearchResponse(total=total, page=1, page_size=page_size, results=[JobSummary.model_validate(j) for j in jobs])


def _load(db: Session, job_id: uuid.UUID) -> Job:
    job = db.scalar(
        select(Job).where(Job.id == job_id)
        .options(joinedload(Job.company), selectinload(Job.sources).selectinload(JobSource.source))
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> JobDetail:
    return JobDetail.model_validate(_load(db, job_id))


@router.get("/{job_id}/sources", response_model=list[JobSourceOut])
def get_job_sources(job_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JobSourceOut]:
    return [JobSourceOut.model_validate(s) for s in _load(db, job_id).sources]
