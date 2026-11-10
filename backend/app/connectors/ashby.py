"""Ashby HQ public job board API connector.

API endpoint: https://api.ashbyhq.com/posting-api/job-board/{board}
One source == one Ashby board slug (e.g. "linear").
"""
import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

API_BASE = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyConnector(BaseConnector):
    """Public Ashby job board API. One source == one board slug."""

    key = "ashby"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        board = config.get("board", "")
        if not re.fullmatch(r"[A-Za-z0-9-]+", board or ""):
            raise ValueError(
                "config.board is required (letters, digits, and hyphens only)"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://jobs.ashbyhq.com/{config['board']}"

    @property
    def _board(self) -> str:
        return self.config["board"]

    async def _fetch_board(self) -> dict[str, Any]:
        data = await self._get_json(f"{API_BASE}/{self._board}")
        if not isinstance(data, dict):
            raise ConnectorError(
                "unexpected Ashby response shape (expected a JSON object)"
            )
        return data

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._fetch_board()
        jobs = data.get("jobs")
        if jobs is None:
            raise ConnectorError("unexpected Ashby response shape (no 'jobs' key)")
        if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
            raise ConnectorError("unexpected Ashby 'jobs' value (expected a list of jobs)")
        return jobs

    async def fetch_company_name(self) -> str | None:
        if self.config.get("company_name"):
            return self.config["company_name"]
        try:
            data = await self._fetch_board()
            org_name = (data.get("organization") or {}).get("name")
            return org_name or self._board.replace("-", " ").title()
        except ConnectorError:
            return self._board.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._fetch_board()
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("id")
        title = (raw.get("title") or "").strip()
        url = raw.get("jobUrl")
        if not job_id or not title or not url:
            raise ValueError("missing id, title, or jobUrl in Ashby posting")

        url = n.canonicalize_url(url)
        location = raw.get("location")
        city, country_code = n.parse_location(location)

        description = n.strip_html(raw.get("descriptionHtml"))

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=description,
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title),
            employment_type=n.normalize_employment_type(raw.get("employmentType")),
            department=raw.get("department"),
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("publishedAt")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
