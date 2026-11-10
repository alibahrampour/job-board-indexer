"""Workable widget API connector with cursor-based pagination.

API: https://apply.workable.com/api/v1/widget/accounts/{subdomain}/jobs
Pagination: results list + hasMore bool + nextPage cursor token.
"""
import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

WIDGET_API = "https://apply.workable.com/api/v1/widget/accounts"


class WorkableConnector(BaseConnector):
    """Workable public widget API with cursor pagination."""

    key = "workable"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        subdomain = config.get("subdomain", "")
        if not subdomain or not isinstance(subdomain, str):
            raise ValueError("config.subdomain is required")
        if not re.fullmatch(r"[A-Za-z0-9-]+", subdomain):
            raise ValueError(
                "config.subdomain must contain only letters, digits, and hyphens"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://apply.workable.com/{config['subdomain']}"

    @property
    def _subdomain(self) -> str:
        return self.config["subdomain"]

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        all_jobs: list[dict[str, Any]] = []
        params: dict[str, Any] = {"limit": 50}
        url = f"{WIDGET_API}/{self._subdomain}/jobs"

        while True:
            data = await self._get_json(url, params=params)
            if not isinstance(data, dict):
                raise ConnectorError(
                    "unexpected Workable response shape (expected a JSON object)"
                )
            results = data.get("results")
            if results is None:
                raise ConnectorError(
                    "unexpected Workable response shape (no 'results' key)"
                )
            if not isinstance(results, list):
                raise ConnectorError(
                    "unexpected Workable 'results' value (not a list)"
                )
            if not all(isinstance(job, dict) for job in results):
                raise ConnectorError(
                    "unexpected Workable 'results' value (invalid job entry)"
                )
            all_jobs.extend(results)

            has_more = data.get("hasMore", False)
            next_page = data.get("nextPage")
            if not has_more or not next_page:
                break

            # Pass the cursor token for the next page
            params = {"limit": 50, "token": next_page}

        return all_jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._subdomain.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(
                f"{WIDGET_API}/{self._subdomain}/jobs", params={"limit": 1}
            )
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        shortcode = raw.get("shortcode") or raw.get("id")
        title = (raw.get("title") or "").strip()
        if not shortcode or not title:
            raise ValueError("missing shortcode/id or title in Workable job")

        url = n.canonicalize_url(
            f"https://apply.workable.com/{self._subdomain}/j/{shortcode}"
        )

        location_obj = raw.get("location") or {}
        if isinstance(location_obj, dict):
            city_raw = location_obj.get("city")
            country_raw = location_obj.get("country")
            location_parts = [p for p in (city_raw, country_raw) if p]
            location = ", ".join(location_parts) if location_parts else None
        else:
            location = str(location_obj)
            city_raw = country_raw = None

        city, country_code = n.parse_location(location)
        if not city and city_raw:
            city = city_raw

        remote_raw = raw.get("remote")
        remote_flag: str | None = None
        if remote_raw is True or str(remote_raw).lower() in ("true", "1", "yes"):
            remote_flag = "remote"

        return NormalizedJob(
            external_id=str(shortcode),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=None,  # widget API doesn't include full description in listing
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title, remote_flag),
            employment_type=n.normalize_employment_type(raw.get("employment_type")),
            department=raw.get("department"),
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("published_on")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
