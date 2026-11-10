import asyncio
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

# Namespace map commonly used in Teamtailor RSS feeds
_NS = {
    "job": "http://www.teamtailor.com/job",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


class TeamtailorConnector(BaseConnector):
    """Teamtailor ATS — RSS XML feed connector."""

    key = "teamtailor"
    platform_type = "ATS"
    connector_type = "http"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        if not (config.get("tenant") or "").strip():
            raise ValueError("config.tenant is required")

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://{config['tenant']}.teamtailor.com"

    @property
    def _tenant(self) -> str:
        return self.config["tenant"]

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get_text(self, url: str) -> str:
        """GET *url* with the same retry/backoff as _get_json; return response text."""
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        last_error = "unknown error"
        for delay in self.RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await self._client.get(url)
            except httpx.TransportError as exc:
                last_error = f"network error: {exc}"
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                last_error = f"HTTP {resp.status_code}"
                retry_after = resp.headers.get("Retry-After", "")
                if retry_after.isdigit():
                    await asyncio.sleep(min(int(retry_after), 60))
                continue
            if resp.status_code in (400, 401, 403, 404):
                raise ConnectorError(
                    f"HTTP {resp.status_code} for {url}", permanent=True
                )
            try:
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as exc:
                raise ConnectorError(f"bad response from {url}: {exc}") from exc
        raise ConnectorError(f"gave up after retries ({last_error}) for {url}")

    # ------------------------------------------------------------------
    # Connector contract
    # ------------------------------------------------------------------

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        url = f"https://{self._tenant}.teamtailor.com/jobs.xml"
        xml_text = await self._get_text(url)
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ConnectorError(f"invalid XML from {url}: {exc}") from exc

        channel = root.find("channel")
        if channel is None:
            raise ConnectorError("RSS feed missing <channel> element")

        jobs: list[dict[str, Any]] = []
        for item in channel.findall("item"):
            raw = _parse_rss_item(item)
            jobs.append(raw)
        return jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._tenant.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_text(f"https://{self._tenant}.teamtailor.com/jobs.xml")
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = str(raw.get("_id") or "").strip()
        title = (raw.get("_title") or "").strip()
        url = (raw.get("_link") or "").strip()

        if not job_id or not title or not url:
            raise ValueError("missing _id, _title or _link in Teamtailor job payload")

        location = raw.get("_location") or None
        city, country_code = n.parse_location(location)
        source_url = n.canonicalize_url(url)

        return NormalizedJob(
            external_id=job_id,
            title=title,
            source_url=source_url,
            apply_url=source_url,
            description=n.strip_html(raw.get("_description")),
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(location, title),
            employment_type=n.normalize_employment_type(title),
            department=raw.get("_department") or None,
            seniority=n.infer_seniority(title),
            posted_at=_parse_rss_date(raw.get("_pubDate")),
            raw_hash=n.compute_raw_hash(raw),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_rss_item(item: ET.Element) -> dict[str, Any]:
    """Extract fields from an RSS <item> into a _-prefixed dict."""

    def txt(tag: str, ns: str | None = None) -> str | None:
        el = item.find(f"{{{ns}}}{tag}") if ns else item.find(tag)
        return (el.text or "").strip() if el is not None and el.text else None

    link = txt("link") or ""
    # Stable ID: sha1 of the canonical URL
    job_id = hashlib.sha1(link.encode()).hexdigest()[:16] if link else ""

    # Try known namespaces for location
    location = (
        txt("location", _NS.get("job"))
        or txt("location", _NS.get("dc"))
        or txt("location")
    )

    return {
        "_id": job_id,
        "_title": txt("title"),
        "_link": link or None,
        "_description": txt("description"),
        "_pubDate": txt("pubDate"),
        "_location": location,
        "_department": txt("department", _NS.get("job")) or txt("department"),
    }


def _parse_rss_date(s: str | None) -> datetime | None:
    """Parse an RFC 2822 pubDate string (e.g. 'Mon, 01 Jan 2026 00:00:00 +0000')."""
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None
