"""Lever ATS public JSON API connector.

API docs: https://hire.lever.co/developer/postings
One source == one Lever company slug (e.g. "stripe").
"""
import re
from datetime import datetime, timezone
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

API_BASE = "https://api.lever.co/v0/postings"


class LeverConnector(BaseConnector):
    """Public Lever job postings API. One source == one company slug."""

    key = "lever"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        company = config.get("company", "")
        if not re.fullmatch(r"[A-Za-z0-9-]+", company or ""):
            raise ValueError(
                "config.company is required (letters, digits, and hyphens only)"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://jobs.lever.co/{config['company']}"

    @property
    def _company(self) -> str:
        return self.config["company"]

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._get_json(
            f"{API_BASE}/{self._company}", params={"mode": "json"}
        )
        if not isinstance(data, list) or not all(isinstance(job, dict) for job in data):
            raise ConnectorError(
                "unexpected Lever response shape (expected a JSON array of jobs)"
            )
        return data

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._company.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(
                f"{API_BASE}/{self._company}", params={"mode": "json", "limit": "1"}
            )
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("id")
        title = (raw.get("text") or "").strip()
        url = raw.get("hostedUrl")
        if not job_id or not title or not url:
            raise ValueError("missing id, text, or hostedUrl in Lever posting")

        url = n.canonicalize_url(url)
        apply_url = raw.get("applyUrl")
        if apply_url:
            apply_url = n.canonicalize_url(apply_url)

        categories = raw.get("categories") or {}
        location = categories.get("location")
        team = categories.get("team")
        commitment = categories.get("commitment")  # employment type

        city, country_code = n.parse_location(location)

        # Lever stores createdAt as Unix milliseconds
        created_ms = raw.get("createdAt")
        posted_at: datetime | None = None
        if created_ms is not None:
            try:
                posted_at = datetime.fromtimestamp(int(created_ms) / 1000, tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                posted_at = None

        description_plain = raw.get("descriptionPlain") or n.strip_html(
            raw.get("description")
        )

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=apply_url,
            description=description_plain,
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title, commitment),
            employment_type=n.normalize_employment_type(commitment),
            department=team,
            seniority=n.infer_seniority(title),
            posted_at=posted_at,
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
