"""Fetch -> Parse -> Validate -> Normalize -> Persist for one source."""
import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.connectors.registry import get_connector_class
from app.database import SessionLocal
from app.models import Company, IngestionRun, Job, JobSource, JobStatus, Source
from app.services import normalization as n

log = logging.getLogger(__name__)


@dataclass
class Counters:
    created: int = 0
    updated: int = 0
    expired: int = 0


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_company(db: Session, name: str) -> Company:
    normalized = n.normalize_company_name(name)
    company = db.scalar(select(Company).where(Company.normalized_name == normalized))
    if company is None:
        company = Company(name=name.strip(), normalized_name=normalized)
        db.add(company)
        db.flush()
    return company


def _apply_fields(job: Job, nj: NormalizedJob, company: Company, now: datetime) -> None:
    job.company_id = company.id
    job.title = nj.title
    job.normalized_title = n.normalize_title(nj.title)
    job.description = nj.description
    job.location = nj.location
    job.city = nj.city
    job.country_code = nj.country_code
    job.remote_type = nj.remote_type
    job.employment_type = nj.employment_type
    job.department = nj.department
    job.seniority = nj.seniority
    job.posted_at = nj.posted_at
    job.last_seen_at = now
    job.status = JobStatus.ACTIVE
    job.quality_score = n.quality_score(
        title=nj.title, company=company.name, apply_url=nj.apply_url or nj.source_url,
        location=nj.location, description=nj.description,
    )


def _refresh_job_status(job: Job) -> bool:
    """Recompute job status from its sources. Returns True if the job just became EXPIRED."""
    previous = job.status
    sources = job.sources
    if any(s.source_status == "ACTIVE" for s in sources):
        job.status = JobStatus.ACTIVE
    elif all(s.source_status == "REMOVED" for s in sources):
        job.status = JobStatus.EXPIRED
    else:
        job.status = JobStatus.PENDING_EXPIRATION
    return job.status == JobStatus.EXPIRED and previous != JobStatus.EXPIRED


def persist_jobs(
    db: Session, source: Source, company: Company, jobs: list[NormalizedJob], *, complete: bool
) -> Counters:
    now = utcnow()
    counters = Counters()
    existing = {
        js.external_job_id: js
        for js in db.scalars(
            select(JobSource)
            .where(JobSource.source_id == source.id)
            .options(selectinload(JobSource.job).selectinload(Job.sources))
        )
    }
    seen: set[str] = set()

    for nj in jobs:
        seen.add(nj.external_id)
        js = existing.get(nj.external_id)
        job_company = get_or_create_company(db, nj.company_name) if nj.company_name else company

        if js is None:
            job = Job(company_id=job_company.id, title=nj.title, normalized_title="")
            _apply_fields(job, nj, job_company, now)
            job.first_seen_at = now
            db.add(job)
            db.flush()
            db.add(JobSource(
                job_id=job.id, source_id=source.id, external_job_id=nj.external_id,
                source_url=nj.source_url, apply_url=nj.apply_url, raw_hash=nj.raw_hash,
                last_seen_at=now,
            ))
            counters.created += 1
            continue

        js.last_seen_at = now
        js.missed_runs = 0
        js.source_status = "ACTIVE"
        if js.raw_hash != nj.raw_hash:
            js.raw_hash = nj.raw_hash
            js.source_url = nj.source_url
            js.apply_url = nj.apply_url
            _apply_fields(js.job, nj, job_company, now)
            counters.updated += 1
        else:
            js.job.last_seen_at = now
            js.job.status = JobStatus.ACTIVE

    # Expiration only after a COMPLETE, non-empty listing. An empty result for a source
    # that previously had jobs is treated as suspect (outage, parser break), never as "all closed".
    suspicious_empty = not jobs and bool(existing)
    if complete and not suspicious_empty:
        for ext_id, js in existing.items():
            if ext_id in seen or js.source_status == "REMOVED":
                continue
            js.missed_runs += 1
            js.source_status = "REMOVED" if js.missed_runs >= settings.expire_after_missed_runs else "MISSING"
            if _refresh_job_status(js.job):
                counters.expired += 1
    return counters


async def _collect(connector: BaseConnector) -> tuple[str | None, list[dict]]:
    async with connector:
        company_name = await connector.fetch_company_name()
        raw_jobs = await connector.fetch_jobs()
        return company_name, raw_jobs


def run_source(source_id: str, trigger: str = "schedule") -> dict:
    with SessionLocal() as db:
        source = db.get(Source, uuid.UUID(source_id))
        if source is None:
            return {"status": "FAILED", "error": "source not found"}

        now = utcnow()
        run = IngestionRun(source_id=source.id, trigger=trigger, status="RUNNING", started_at=now)
        source.last_run_at = now
        db.add(run)
        db.commit()

        try:
            connector = get_connector_class(source.connector)(source.config or {})
            company_name, raw_jobs = asyncio.run(_collect(connector))
            run.jobs_found = len(raw_jobs)

            parsed: list[NormalizedJob] = []
            for raw in raw_jobs:
                try:
                    parsed.append(connector.parse_job(raw))
                except Exception as exc:  # one bad record must not sink the run
                    run.jobs_failed += 1
                    log.warning("parse failed source=%s: %s", source.name, exc)

            company = get_or_create_company(db, company_name or source.name)
            if source.company_id is None:
                source.company_id = company.id

            # If many records failed to parse, the listing is not trustworthy for expiration.
            complete = run.jobs_failed == 0
            counters = persist_jobs(db, source, company, parsed, complete=complete)

            run.jobs_created, run.jobs_updated, run.jobs_expired = (
                counters.created, counters.updated, counters.expired,
            )
            run.status = "SUCCESS" if run.jobs_failed == 0 else "PARTIAL"
            source.last_success_at = utcnow()
            source.last_error_message = None
        except Exception as exc:
            db.rollback()
            log.exception("ingestion failed source=%s", source.name)
            run.status = "FAILED"
            run.error_message = str(exc)[:2000]
            source.last_error_at = utcnow()
            source.last_error_message = str(exc)[:2000]
            if isinstance(exc, ConnectorError) and exc.permanent:
                log.error("permanent error for %s; consider disabling the source", source.name)
        finally:
            run.finished_at = utcnow()
            db.commit()

        return {
            "run_id": str(run.id), "status": run.status, "found": run.jobs_found,
            "created": run.jobs_created, "updated": run.jobs_updated,
            "failed": run.jobs_failed, "expired": run.jobs_expired,
        }
