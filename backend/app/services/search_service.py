import uuid
from datetime import timedelta

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, contains_eager, selectinload

from app.models import Company, Job, JobSource, JobStatus
from app.services.ingestion import utcnow

VISIBLE_STATUSES = (JobStatus.ACTIVE, JobStatus.PENDING_EXPIRATION)


def search_jobs(
    db: Session,
    *,
    q: str | None = None,
    location: str | None = None,
    remote_type: str | None = None,
    employment_type: str | None = None,
    seniority: str | None = None,
    company: str | None = None,
    company_id: uuid.UUID | None = None,
    posted_within_days: int | None = None,
    sort: str = "relevance",
    page: int = 1,
    page_size: int = 20,
) -> tuple[int, list[Job]]:
    conds = [Job.status.in_(VISIBLE_STATUSES)]
    ts_query = None

    if q and q.strip():
        ts_query = func.websearch_to_tsquery("simple", q.strip())
        conds.append(Job.search_vector.op("@@")(ts_query))
    if location:
        like = f"%{location.strip()}%"
        conds.append(or_(Job.location.ilike(like), Job.city.ilike(like), Job.country_code == location.strip().upper()))
    if remote_type:
        conds.append(Job.remote_type == remote_type.upper())
    if employment_type:
        conds.append(Job.employment_type == employment_type.upper())
    if seniority:
        conds.append(Job.seniority == seniority.upper())
    if company:
        conds.append(Company.name.ilike(f"%{company.strip()}%"))
    if company_id:
        conds.append(Job.company_id == company_id)
    if posted_within_days:
        conds.append(func.coalesce(Job.posted_at, Job.first_seen_at) >= utcnow() - timedelta(days=posted_within_days))

    total = db.scalar(select(func.count()).select_from(Job).join(Company).where(*conds)) or 0

    stmt: Select = (
        select(Job)
        .join(Company)
        .where(*conds)
        .options(contains_eager(Job.company), selectinload(Job.sources).selectinload(JobSource.source))
    )
    newest = func.coalesce(Job.posted_at, Job.first_seen_at).desc()
    if ts_query is not None and sort == "relevance":
        stmt = stmt.order_by(func.ts_rank_cd(Job.search_vector, ts_query).desc(), Job.quality_score.desc(), newest)
    else:
        stmt = stmt.order_by(newest)

    rows = db.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique().all()
    return total, list(rows)
