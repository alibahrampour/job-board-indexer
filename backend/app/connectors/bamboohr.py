import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n


class BambooHRConnector(BaseConnector):
    """BambooHR JSON careers API. One source == one company subdomain."""

    key = "bamboohr"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        company = config.get("company", "")
        if not re.fullmatch(r"[A-Za-z0-9-]+", company or ""):
            raise ValueError(
                "config.company is required (letters, digits and hyphens only)"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://{config['company']}.bamboohr.com/jobs"

    @property
    def _company(self) -> str:
        return self.config["company"]

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        url = f"https://{self._company}.bamboohr.com/careers/list"
        data = await self._get_json(url)
        jobs = data.get("result") if isinstance(data, dict) else None
        if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
            raise ConnectorError(
                "unexpected BambooHR response shape (expected a 'result' list)"
            )
        return jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._company.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(f"https://{self._company}.bamboohr.com/careers/list")
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = str(raw.get("id") or "").strip()
        title = (raw.get("jobOpeningName") or "").strip()
        url = f"https://{self._company}.bamboohr.com/careers/{job_id}"

        if not job_id or not title:
            raise ValueError("missing id or title in BambooHR job payload")

        city_raw = raw.get("locationCity") or ""
        country_raw = raw.get("locationCountry") or ""
        location = ", ".join(filter(None, [city_raw, country_raw])) or None
        city, country_code = n.parse_location(location)

        source_url = n.canonicalize_url(url)

        return NormalizedJob(
            external_id=job_id,
            title=title,
            source_url=source_url,
            apply_url=source_url,
            description=n.strip_html(raw.get("jobDescription")),
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title),
            employment_type=n.normalize_employment_type(title),
            department=raw.get("department") or None,
            seniority=n.infer_seniority(title),
            posted_at=_parse_date(raw.get("datePosted")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_date(value: str | None) -> datetime | None:
    """Parse a YYYY-MM-DD date string returned by BambooHR."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None
