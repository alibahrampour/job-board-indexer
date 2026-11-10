import asyncio
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

# Common RSS namespace URIs used by WP Job Manager
_NS = {
    "job_listing": "https://wpjobmanager.com/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "georss": "http://www.georss.org/georss",
}


class WPJobManagerConnector(BaseConnector):
    """WordPress WP Job Manager RSS feed connector."""

    key = "wp_job_manager"
    platform_type = "JOB_BOARD"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        feed_url = config.get("feed_url", "")
        if not feed_url or not str(feed_url).startswith("http"):
            raise ValueError(
                "config.feed_url is required and must start with 'http'"
            )

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return config["feed_url"].split("?")[0]

    @property
    def _feed_url(self) -> str:
        return self.config["feed_url"]

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
        xml_text = await self._get_text(self._feed_url)
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ConnectorError(
                f"invalid XML from {self._feed_url}: {exc}"
            ) from exc

        channel = root.find("channel")
        if channel is None:
            raise ConnectorError("RSS feed missing <channel> element")

        return [_parse_rss_item(item) for item in channel.findall("item")]

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name")

    async def health_check(self) -> bool:
        try:
            await self._get_text(self._feed_url)
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        job_id = str(raw.get("_id") or "").strip()
        title = (raw.get("_title") or "").strip()
        url = (raw.get("_link") or "").strip()

        if not job_id or not title or not url:
            raise ValueError(
                "missing _id, _title or _link in WP Job Manager job payload"
            )

        location = raw.get("_location") or None
        city, country_code = n.parse_location(location)
        source_url = n.canonicalize_url(url)

        return NormalizedJob(
            external_id=job_id,
            title=title,
            source_url=source_url,
            apply_url=source_url,
            company_name=raw.get("_company") or None,
            description=n.strip_html(raw.get("_description")),
            location=location,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(
                location, title, raw.get("_job_type") or ""
            ),
            employment_type=n.normalize_employment_type(
                raw.get("_job_type") or title
            ),
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
    job_id = hashlib.sha1(link.encode()).hexdigest()[:16] if link else ""

    # Try multiple namespace URIs that WP Job Manager plugins use
    ns_wjm = _NS["job_listing"]
    location = (
        txt("job_location", ns_wjm)
        or txt("location", ns_wjm)
        or txt("location")
    )
    job_type = txt("job_type", ns_wjm) or txt("job_type")
    company = txt("company", ns_wjm) or txt("company")

    return {
        "_id": job_id,
        "_title": txt("title"),
        "_link": link or None,
        "_description": txt("description"),
        "_pubDate": txt("pubDate"),
        "_location": location,
        "_job_type": job_type,
        "_company": company,
        "_job_expires": txt("job_expires", ns_wjm) or txt("job_expires"),
    }


def _parse_rss_date(s: str | None) -> datetime | None:
    """Parse an RFC 2822 pubDate string (e.g. 'Mon, 01 Jan 2026 00:00:00 +0000')."""
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        return None
