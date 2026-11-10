"""Ingestion pipeline: Fetch -> Parse -> Validate -> Normalize -> Persist."""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.models import Company, IngestionRun, Job, JobSource, JobStatus, Source
from app.schemas.job import ParsedJob
from app.services import normalization as norm

log = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_parsed(parsed: ParsedJob) -> dict:
    city, country = norm.parse_location(parsed.location)
    return {
        "title": parsed.title,
        "normalized_title": norm.normalize_title(parsed.title),
        "description": norm.html_to_text(parsed.description_html),
        "location": parsed.location,
        "city": city,
        "country_code": country,
        "remote_type": norm.normalize_remote_type(parsed.location, parsed.title),
        "employment_type": norm.normalize_employment_type(parsed.employment_type_raw),
        "department": parsed.department,
        "seniority": norm.detect_seniority(parsed.title),
        "posted_at": parsed.posted_at,
    }


def get_or_create_company(session: Session, name: str) -> Company:
    normalized = norm.normalize_company_name(name)
    company = session.scalar(select(Company).where(Company.normalized_name == normalized))
    if company is None:
        company = Company(name=name, normalized_name=normalized)
        session.add(company)
        session.flush()
    return company


def upsert_job(session: Session, source: Source, company: Company, parsed: ParsedJob, now: datetime) -> str:
    """Returns 'created', 'updated' or 'unchanged'. Exact match on (source, external id)."""
    raw_hash = norm.compute_raw_hash(parsed.raw)
    fields = normalize_parsed(parsed)
    job_source = session.scalar(
        select(JobSource).where(
            JobSource.source_id == source.id,
            JobSource.external_job_id == parsed.external_id,
        )
    )

    if job_source is None:
        job = Job(
            company_id=company.id,
            first_seen_at=now,
            last_seen_at=now,
            status=JobStatus.ACTIVE,
            **fields,
        )
        session.add(job)
        session.flush()
        session.add(
            JobSource(
                job_id=job.id,
                source_id=source.id,
                external_job_id=parsed.external_id,
                source_url=norm.canonicalize_url(parsed.source_url),
                apply_url=parsed.apply_url,
                raw_hash=raw_hash,
                last_seen_at=now,
            )
        )
        return "created"

    job = job_source.job
    job_source.last_seen_at = now
    job_source.source_status = "ACTIVE"
    job.last_seen_at = now
    job.status = JobStatus.ACTIVE

    if job_source.raw_hash == raw_hash:
        return "unchanged"

    for key, value in fields.items():
        setattr(job, key, value)
    job.company_id = company.id
    job_source.raw_hash = raw_hash
    job_source.source_url = norm.canonicalize_url(parsed.source_url)
    job_source.apply_url = parsed.apply_url
    return "updated"


def ingest_source(session: Session, source_id: uuid.UUID) -> IngestionRun | None:
    source = session.get(Source, source_id)
    if source is None or not source.is_active:
        return None

    started = utcnow()
    run = IngestionRun(source_id=source.id, started_at=started, status="RUNNING")
    session.add(run)
    source.last_started_at = started
    session.commit()

    # Fetch. If this fails we know nothing about the source's jobs, so we touch nothing.
    try:
        connector = get_connector(source)
        raw_jobs = asyncio.run(connector.fetch_jobs())
    except Exception as exc:  # noqa: BLE001 - any fetch failure is recorded, not raised
        log.exception("fetch failed for source %s", source.name)
        session.rollback()
        run.status = "FAILED"
        run.finished_at = utcnow()
        run.error_message = f"{type(exc).__name__}: {exc}"[:2000]
        source.last_error_at = run.finished_at
        source.last_error_message = run.error_message
        session.commit()
        return run

    run.jobs_found = len(raw_jobs)
    created = updated = failed = 0
    now = utcnow()

    for raw in raw_jobs:
        try:
            parsed = connector.parse_job(raw)
            with session.begin_nested():
                company = get_or_create_company(session, parsed.company_name)
                outcome = upsert_job(session, source, company, parsed, now)
        except Exception:  # noqa: BLE001 - one bad job must not abort the run
            failed += 1
            log.exception("failed to process job from %s: %s", source.name, str(raw)[:200])
            continue
        if outcome == "created":
            created += 1
        elif outcome == "updated":
            updated += 1

    run.jobs_created, run.jobs_updated, run.jobs_failed = created, updated, failed
    run.status = "SUCCESS" if failed == 0 else "PARTIAL"
    run.finished_at = utcnow()
    source.last_success_at = run.finished_at
    if failed == 0:
        source.last_error_message = None
    session.commit()
    return run
