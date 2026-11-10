"""SmartRecruiters public postings API connector with offset pagination.

API: https://api.smartrecruiters.com/v1/companies/{company_id}/postings
One source == one SmartRecruiters company identifier (e.g. "COMPANY").
"""
import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

API_BASE = "https://api.smartrecruiters.com/v1/companies"
JOB_URL_BASE = "https://jobs.smartrecruiters.com"
PAGE_SIZE = 100


class SmartRecruitersConnector(BaseConnector):
    """Public SmartRecruiters postings API with offset pagination."""

    key = "smartrecruiters"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        company_id = config.get("company_id", "")
        if not company_id or not isinstance(company_id, str):
            raise ValueError("config.company_id is required")

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://careers.smartrecruiters.com/{config['company_id']}"

    @property
    def _company_id(self) -> str:
        return self.config["company_id"]

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        offset = 0
        while True:
            data = await self._get_json(
                f"{API_BASE}/{self._company_id}/postings",
                params={"limit": PAGE_SIZE, "offset": offset},
            )
            if not isinstance(data, dict):
                raise ConnectorError(
                    "unexpected SmartRecruiters response shape (expected a JSON object)"
                )
            content = data.get("content")
            if not isinstance(content, list) or not all(isinstance(job, dict) for job in content):
                raise ConnectorError(
                    "unexpected SmartRecruiters response shape (expected a 'content' list of jobs)"
                )
            if not content:
                break
            all_jobs.extend(content)
            # If we got fewer than PAGE_SIZE items, we're done
            if len(content) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
        return all_jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._company_id.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(
                f"{API_BASE}/{self._company_id}/postings",
                params={"limit": 1, "offset": 0},
            )
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("id")
        title = (raw.get("name") or "").strip()
        if not job_id or not title:
            raise ValueError("missing id or name in SmartRecruiters posting")

        url = n.canonicalize_url(
            f"{JOB_URL_BASE}/{self._company_id}/{job_id}"
        )

        location_obj = raw.get("location") or {}
        city_raw = location_obj.get("city")
        country_raw = location_obj.get("country")
        # Build a combined location string for normalization
        location_parts = [p for p in (city_raw, country_raw) if p]
        location = ", ".join(location_parts) if location_parts else None
        city, country_code = n.parse_location(location)
        # Prefer the raw city value if parse_location didn't extract one
        if not city and city_raw:
            city = city_raw

        department = (raw.get("department") or {}).get("label")
        employment_type_label = (raw.get("typeOfEmployment") or {}).get("label")

        # Description: SmartRecruiters doesn't return full description in list,
        # so we strip whatever we have.
        job_ad_sections = (raw.get("jobAd") or {}).get("sections") or {}
        if isinstance(job_ad_sections, dict):
            description_parts = []
            for section_value in job_ad_sections.values():
                if isinstance(section_value, dict):
                    html = section_value.get("html") or section_value.get("text") or ""
                else:
                    html = str(section_value)
                stripped = n.strip_html(html)
                if stripped:
                    description_parts.append(stripped)
            description = "\n\n".join(description_parts) if description_parts else None
        else:
            description = n.strip_html(str(job_ad_sections)) if job_ad_sections else None

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
            employment_type=n.normalize_employment_type(employment_type_label),
            department=department,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("releasedDate")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
