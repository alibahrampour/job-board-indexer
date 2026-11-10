"""Breezy HR JSON API connector.

API: https://{company}.breezy.hr/json
One source == one Breezy company slug (e.g. "mycompany").
"""
import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n


class BreezyConnector(BaseConnector):
    """Public Breezy HR JSON feed. One source == one company slug."""

    key = "breezy"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        company = config.get("company", "")
        if not company or not isinstance(company, str):
            raise ValueError("config.company is required")
        if not re.fullmatch(r"[A-Za-z0-9-]+", company):
            raise ValueError(
                "config.company must contain only letters, digits, and hyphens"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://{config['company']}.breezy.hr"

    @property
    def _company(self) -> str:
        return self.config["company"]

    @property
    def _json_url(self) -> str:
        return f"https://{self._company}.breezy.hr/json"

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._get_json(self._json_url)
        if not isinstance(data, list) or not all(isinstance(job, dict) for job in data):
            raise ConnectorError(
                "unexpected Breezy response shape (expected a JSON array of jobs)"
            )
        return data

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._company.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(self._json_url)
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("_id") or raw.get("id")
        title = (raw.get("name") or "").strip()
        if not job_id or not title:
            raise ValueError("missing _id/id or name in Breezy posting")

        url = n.canonicalize_url(f"https://{self._company}.breezy.hr/p/{job_id}")

        location_obj = raw.get("location") or {}
        location = location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj)
        city, country_code = n.parse_location(location)

        department_obj = raw.get("department") or {}
        department = department_obj.get("name") if isinstance(department_obj, dict) else None

        type_obj = raw.get("type") or {}
        employment_type_raw = type_obj.get("name") if isinstance(type_obj, dict) else None

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=None,  # /json feed doesn't include full description
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title, employment_type_raw),
            employment_type=n.normalize_employment_type(employment_type_raw),
            department=department,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("creation_date")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
