"""Recruitee ATS public offers API connector.

API: https://{tenant}.recruitee.com/api/offers/
One source == one Recruitee tenant slug (e.g. "mycompany").
"""
import re
from datetime import datetime
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n


class RecruiteeConnector(BaseConnector):
    """Public Recruitee offers API. One source == one tenant slug."""

    key = "recruitee"
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
        return f"https://{config['tenant']}.recruitee.com"

    @property
    def _tenant(self) -> str:
        return self.config["tenant"]

    @property
    def _api_url(self) -> str:
        return f"https://{self._tenant}.recruitee.com/api/offers/"

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        data = await self._get_json(self._api_url)
        if not isinstance(data, dict):
            raise ConnectorError(
                "unexpected Recruitee response shape (expected a JSON object)"
            )
        offers = data.get("offers")
        if offers is None:
            raise ConnectorError(
                "unexpected Recruitee response shape (no 'offers' key)"
            )
        if not isinstance(offers, list) or not all(isinstance(offer, dict) for offer in offers):
            raise ConnectorError(
                "unexpected Recruitee 'offers' value (expected a list of offers)"
            )
        return offers

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._tenant.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_json(self._api_url)
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("id")
        title = (raw.get("title") or "").strip()
        url = raw.get("careers_url")
        if not job_id or not title or not url:
            raise ValueError("missing id, title, or careers_url in Recruitee offer")

        url = n.canonicalize_url(url)

        # Recruitee provides city and country_code as top-level fields
        city_raw = raw.get("city")
        country_code_raw = raw.get("country_code")
        location = raw.get("location")

        # If location string is not provided, build one from city + country
        if not location:
            parts = [p for p in (city_raw, country_code_raw) if p]
            location = ", ".join(parts) if parts else None

        city, country_code = n.parse_location(location)
        # Prefer the explicit Recruitee fields when available
        if not city and city_raw:
            city = city_raw
        if not country_code and country_code_raw:
            country_code = country_code_raw

        # remote: Recruitee returns a boolean or string
        remote_raw = raw.get("remote")
        remote_flag: str | None = None
        if remote_raw is True or str(remote_raw).lower() in ("true", "1", "yes"):
            remote_flag = "remote"

        description = n.strip_html(raw.get("description"))

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=description,
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title, remote_flag),
            employment_type=n.normalize_employment_type(raw.get("kind")),
            department=raw.get("department"),
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("published_at")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
