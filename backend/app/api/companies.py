import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Company, Job
from app.schemas import CompanyDetail, CompanyOut, JobSummary, SearchResponse
from app.services.search_service import VISIBLE_STATUSES, search_jobs

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


def _detail(company: Company, active_jobs: int) -> CompanyDetail:
    return CompanyDetail(**CompanyOut.model_validate(company).model_dump(), active_jobs=active_jobs)


@router.get("", response_model=list[CompanyDetail])
def list_companies(
    q: str | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)
) -> list[CompanyDetail]:
    counts = (
        select(Job.company_id, func.count().label("n"))
        .where(Job.status.in_(VISIBLE_STATUSES))
        .group_by(Job.company_id)
        .subquery()
    )
    n = func.coalesce(counts.c.n, 0)
    stmt = select(Company, n).outerjoin(counts, counts.c.company_id == Company.id)
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q.strip()}%"))
    rows = db.execute(stmt.order_by(n.desc(), Company.name).limit(limit)).all()
    return [_detail(c, count) for c, count in rows]


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)) -> CompanyDetail:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    count = db.scalar(
        select(func.count()).select_from(Job).where(Job.company_id == company_id, Job.status.in_(VISIBLE_STATUSES))
    )
    return _detail(company, count or 0)


@router.get("/{company_id}/jobs", response_model=SearchResponse)
def company_jobs(
    company_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    total, jobs = search_jobs(db, company_id=company_id, sort="newest", page=page, page_size=page_size)
    return SearchResponse(
        total=total, page=page, page_size=page_size, results=[JobSummary.model_validate(j) for j in jobs]
    )
