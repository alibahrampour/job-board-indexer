import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

API = "https://boards-api.greenhouse.io/v1/boards"


class GreenhouseConnector(BaseConnector):
    """Public Greenhouse Job Board API. One source == one company board token."""

    key = "greenhouse"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        token = config.get("board_token", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", token or ""):
            raise ValueError("config.board_token is required (letters, digits, - and _)")

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://boards.greenhouse.io/{config['board_token']}"

    @property
    def _token(self) -> str:
        return self.config["board_token"]

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._get_json(f"{API}/{self._token}/jobs", params={"content": "true"})
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
            raise ConnectorError("unexpected Greenhouse response shape (expected a 'jobs' list)")
        return jobs

    async def fetch_company_name(self) -> str | None:
        if self.config.get("company_name"):
            return self.config["company_name"]
        try:
            data = await self._get_json(f"{API}/{self._token}")
            return data.get("name") or self._token.replace("-", " ").title()
        except ConnectorError:
            return self._token.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(f"{API}/{self._token}/jobs")
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        title = (raw.get("title") or "").strip()
        url = raw.get("absolute_url")
        if not raw.get("id") or not title or not url:
            raise ValueError("missing id, title or absolute_url")

        location = (raw.get("location") or {}).get("name")
        city, country = n.parse_location(location)
        departments = [d.get("name") for d in raw.get("departments") or [] if d.get("name")]
        url = n.canonicalize_url(url)

        return NormalizedJob(
            external_id=str(raw["id"]),
            title=title,
            source_url=url,
            apply_url=url,
            description=n.strip_html(raw.get("content")),
            location=location,
            city=city,
            country_code=country,
            remote_type=n.detect_remote_type(location, title),
            employment_type=n.normalize_employment_type(title),
            department=departments[0] if departments else None,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("first_published") or raw.get("updated_at")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
