"""Pinpoint HQ JSON postings API connector.

API: https://{tenant}.pinpointhq.com/postings.json
Response may be a plain list or {"data": [...]} envelope.
One source == one Pinpoint tenant slug (e.g. "mycompany").
"""
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n


class PinpointConnector(BaseConnector):
    """Public Pinpoint HQ postings API. One source == one tenant slug."""

    key = "pinpoint"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        tenant = config.get("tenant", "")
        if not tenant or not isinstance(tenant, str):
            raise ValueError("config.tenant is required")
        if not re.fullmatch(r"[A-Za-z0-9-]+", tenant):
            raise ValueError(
                "config.tenant must contain only letters, digits, and hyphens"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://{config['tenant']}.pinpointhq.com"

    @property
    def _tenant(self) -> str:
        return self.config["tenant"]

    @property
    def _postings_url(self) -> str:
        return f"https://{self._tenant}.pinpointhq.com/postings.json"

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._get_json(self._postings_url)
        # Accept both a plain list and a {"data": [...]} envelope
        if isinstance(data, list):
            if not all(isinstance(job, dict) for job in data):
                raise ConnectorError("unexpected Pinpoint response shape (invalid job entry)")
            return data
        if isinstance(data, dict):
            jobs = data.get("data")
            if isinstance(jobs, list) and all(isinstance(job, dict) for job in jobs):
                return jobs
            raise ConnectorError(
                "unexpected Pinpoint response shape (dict has no 'data' list)"
            )
        raise ConnectorError(
            "unexpected Pinpoint response shape (expected list or object)"
        )

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._tenant.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(self._postings_url)
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        # Support both flat and nested "attributes" shapes
        attrs = raw.get("attributes") or {}

        job_id = raw.get("id")
        title = (
            (raw.get("title") or attrs.get("job_title") or "")
        ).strip()
        if not job_id or not title:
            raise ValueError("missing id or title in Pinpoint posting")

        posting_url = raw.get("url") or raw.get("path")
        if posting_url:
            posting_url = urljoin(
                f"https://{self._tenant}.pinpointhq.com/",
                str(posting_url),
            )
        else:
            posting_url = f"https://{self._tenant}.pinpointhq.com/postings/{job_id}"
        url = n.canonicalize_url(posting_url)

        location_value = raw.get("location") or attrs.get("location")
        if isinstance(location_value, dict):
            location = location_value.get("name") or ", ".join(
                str(location_value[key])
                for key in ("city", "province", "country", "postal_code")
                if location_value.get(key)
            )
        elif isinstance(location_value, str):
            location = location_value
        else:
            location = None

        city, country_code = n.parse_location(location)

        department = raw.get("department") or attrs.get("team")

        employment_type_raw = raw.get("employment_type") or attrs.get("employment_type")

        posted_at_raw = raw.get("published_at") or attrs.get("published_at")

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=n.strip_html(raw.get("description")),
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title),
            employment_type=n.normalize_employment_type(employment_type_raw),
            department=department,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(posted_at_raw),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
