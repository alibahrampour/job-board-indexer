import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CompanyOut(ORM):
    id: uuid.UUID
    name: str
    website: str | None = None
    logo_url: str | None = None
    industry: str | None = None


class CompanyDetail(CompanyOut):
    active_jobs: int = 0


class JobSourceOut(ORM):
    id: uuid.UUID
    platform: str
    source_url: str
    apply_url: str | None = None
    source_status: str
    last_seen_at: datetime


class JobSummary(ORM):
    id: uuid.UUID
    title: str
    company: CompanyOut
    location: str | None = None
    city: str | None = None
    country_code: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    department: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    posted_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    status: str
    apply_url: str | None = None
    platform: str | None = None


class JobDetail(JobSummary):
    description: str | None = None
    quality_score: int
    sources: list[JobSourceOut] = Field(default_factory=list)


class SearchResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[JobSummary]


class SourceOut(ORM):
    id: uuid.UUID
    name: str
    platform_type: str
    connector: str
    connector_type: str
    base_url: str | None = None
    is_active: bool
    schedule_minutes: int
    last_run_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_message: str | None = None


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector: str = "greenhouse"
    config: dict = Field(default_factory=dict, description='e.g. {"board_token": "airbnb"}')
    schedule_minutes: int = Field(default=360, ge=5)


class IngestionRunOut(ORM):
    id: uuid.UUID
    source_id: uuid.UUID
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    jobs_found: int
    jobs_created: int
    jobs_updated: int
    jobs_failed: int
    jobs_expired: int
    error_message: str | None = None
