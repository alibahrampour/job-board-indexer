"""Personio public job feed connector.

Attempts JSON first (application/json Accept header), falls back to XML.
API: https://{tenant}.jobs.personio.de/api/v1/jobs  (JSON)
     https://{tenant}.jobs.personio.de/xml           (XML fallback)
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n


class PersonioConnector(BaseConnector):
    """Personio public job feed. Supports JSON and XML responses."""

    key = "personio"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        tenant = config.get("tenant", "")
        if not re.fullmatch(r"[A-Za-z0-9-]+", tenant or ""):
            raise ValueError(
                "config.tenant is required (letters, digits, and hyphens only)"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://{config['tenant']}.jobs.personio.de"

    @property
    def _tenant(self) -> str:
        return self.config["tenant"]

    @property
    def _json_url(self) -> str:
        return f"https://{self._tenant}.jobs.personio.de/api/v1/jobs"

    @property
    def _xml_url(self) -> str:
        return f"https://{self._tenant}.jobs.personio.de/xml"

    async def _fetch_xml_jobs(self) -> list[dict[str, Any]]:
        """Fetch and parse the XML feed, normalizing to a common dict shape."""
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        try:
            resp = await self._client.get(
                self._xml_url, headers={"Accept": "application/xml, text/xml, */*"}
            )
        except httpx.TransportError as exc:
            raise ConnectorError(f"network error fetching XML feed: {exc}") from exc

        if resp.status_code in (400, 401, 403, 404):
            raise ConnectorError(
                f"HTTP {resp.status_code} for {self._xml_url}", permanent=True
            )
        if not resp.is_success:
            raise ConnectorError(f"HTTP {resp.status_code} for {self._xml_url}")

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as exc:
            raise ConnectorError(f"failed to parse Personio XML: {exc}") from exc

        jobs: list[dict[str, Any]] = []
        # Support both <positions> and <jobs> as root/wrapper element names
        positions = root.findall(".//position") or root.findall(".//job")
        for pos in positions:
            def txt(tag: str) -> str | None:
                el = pos.find(tag)
                return el.text.strip() if el is not None and el.text else None

            raw: dict[str, Any] = {
                "_src": "xml",
                "id": txt("id"),
                "attributes": {
                    "name": txt("title") or txt("name"),
                    "employment_type": txt("schedule") or txt("employment_type"),
                    "created_at": txt("created_at") or txt("createdAt"),
                    "location": txt("office") or txt("location"),
                    "department": {
                        "attributes": {"name": txt("department")}
                    },
                    "office": {
                        "attributes": {
                            "name": txt("office"),
                            "country": txt("country"),
                        }
                    },
                },
            }
            jobs.append(raw)
        return jobs

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        # Try JSON first
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        try:
            resp = await self._client.get(
                self._json_url, headers={"Accept": "application/json"}
            )
        except httpx.TransportError as exc:
            raise ConnectorError(f"network error: {exc}") from exc

        if resp.status_code == 404:
            # JSON endpoint not available — fall back to XML
            return await self._fetch_xml_jobs()

        if resp.status_code in (400, 401, 403):
            raise ConnectorError(
                f"HTTP {resp.status_code} for {self._json_url}", permanent=True
            )
        if resp.status_code == 429 or resp.status_code >= 500:
            raise ConnectorError(f"HTTP {resp.status_code} for {self._json_url}")

        try:
            data = resp.json()
        except ValueError:
            # Non-JSON body — try XML fallback
            return await self._fetch_xml_jobs()

        jobs = data.get("data") if isinstance(data, dict) else None
        if not isinstance(jobs, list) or not all(isinstance(job, dict) for job in jobs):
            # Unexpected shape — try XML fallback
            return await self._fetch_xml_jobs()

        return jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._tenant.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self.fetch_jobs()
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = raw.get("id")
        attrs = raw.get("attributes") or {}

        title = (attrs.get("name") or "").strip()
        if not job_id or not title:
            raise ValueError("missing id or attributes.name in Personio posting")

        url = n.canonicalize_url(
            f"https://{self._tenant}.jobs.personio.de/{job_id}"
        )

        # Location: prefer office name + country
        office = (attrs.get("office") or {}).get("attributes") or {}
        office_name = office.get("name")
        country_raw = office.get("country")
        location_parts = [p for p in (office_name, country_raw) if p]
        location = ", ".join(location_parts) if location_parts else attrs.get("location")

        city, country_code = n.parse_location(location)

        department = None
        dept_obj = attrs.get("department")
        if isinstance(dept_obj, dict):
            department = (dept_obj.get("attributes") or {}).get("name")

        employment_type_raw = attrs.get("employment_type")

        return NormalizedJob(
            external_id=str(job_id),
            title=n.normalize_title(title),
            source_url=url,
            apply_url=url,
            description=None,  # Personio feed doesn't include description in listing
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title, employment_type_raw),
            employment_type=n.normalize_employment_type(employment_type_raw),
            department=department,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(attrs.get("created_at")),
            raw_hash=n.compute_raw_hash(raw),
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
