import asyncio
import hashlib
import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

_NEXT_DATA_RE = re.compile(
    r'<script\s+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.DOTALL,
)

# Ordered list of paths to try when navigating __NEXT_DATA__ for jobs
_JOB_LIST_PATHS: list[list[str]] = [
    ["props", "pageProps", "jobs"],
    ["props", "pageProps", "initialData", "jobs"],
    ["props", "pageProps", "data", "jobs"],
    ["props", "pageProps", "jobListings"],
]


class RipplingConnector(BaseConnector):
    """Rippling ATS — extracts job data from embedded __NEXT_DATA__ JSON."""

    key = "rippling"
    platform_type = "ATS"
    connector_type = "http"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        company = config.get("company", "")
        if not isinstance(company, str) or not re.fullmatch(r"[A-Za-z0-9-]+", company):
            raise ValueError("config.company is required (letters, digits, and hyphens only)")

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        return f"https://ats.rippling.com/{config['company']}/jobs"

    @property
    def _company(self) -> str:
        return self.config["company"]

    @property
    def _jobs_url(self) -> str:
        return f"https://ats.rippling.com/{self._company}/jobs"

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _get_html(self, url: str) -> str:
        """GET *url* accepting HTML; retries on transient errors."""
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        last_error = "unknown error"
        for delay in self.RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await self._client.get(
                    url, headers={"Accept": "text/html,application/xhtml+xml,*/*"}
                )
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
        html = await self._get_html(self._jobs_url)
        m = _NEXT_DATA_RE.search(html)
        if not m:
            raise ConnectorError(
                "Could not find job data in page (__NEXT_DATA__ script tag missing)",
                permanent=False,
            )

        try:
            data: dict[str, Any] = json.loads(m.group(1))
        except json.JSONDecodeError as exc:
            raise ConnectorError(
                f"Could not parse __NEXT_DATA__ JSON: {exc}"
            ) from exc

        jobs = _extract_jobs(data)
        if jobs is None:
            raise ConnectorError(
                "Could not find job data in page (no recognisable job list in __NEXT_DATA__)",
                permanent=False,
            )

        return jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._company.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            await self._get_html(self._jobs_url)
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        # Rippling may expose different field names; try multiple
        job_id = (
            str(raw.get("id") or raw.get("jobId") or raw.get("slug") or "").strip()
        )
        title = (raw.get("title") or raw.get("jobTitle") or raw.get("name") or "").strip()
        url_path = raw.get("url") or raw.get("link") or raw.get("path") or ""
        tenant_root = f"https://ats.rippling.com/{self._company}/"
        if url_path.startswith("/"):
            url = urljoin(tenant_root, url_path.lstrip("/"))
        else:
            url = urljoin(tenant_root, url_path)

        # Fall back to URL hash for ID when missing
        if not job_id and url:
            job_id = hashlib.sha1(url.encode()).hexdigest()[:16]

        if not job_id or not title or not url:
            raise ValueError(
                "missing id, title or url in Rippling job payload"
            )

        location_value = (
            raw.get("location")
            or raw.get("locationName")
            or raw.get("office")
            or raw.get("locations")
        )
        location_data: dict[str, Any] = {}
        if isinstance(location_value, dict):
            location_data = location_value
            location = (
                location_data.get("name")
                or ", ".join(
                    str(location_data[key])
                    for key in ("city", "state", "country")
                    if location_data.get(key)
                )
                or None
            )
        elif isinstance(location_value, list):
            locations = [item for item in location_value if isinstance(item, dict)]
            location_data = locations[0] if locations else {}
            location = "; ".join(
                str(item["name"])
                for item in locations
                if item.get("name")
            ) or None
        else:
            location = location_value

        city, country_code = n.parse_location(location)
        country_code = country_code or location_data.get("countryCode")
        department = raw.get("department") or raw.get("team")
        if isinstance(department, dict):
            department = department.get("name")
        source_url = n.canonicalize_url(url)

        return NormalizedJob(
            external_id=job_id,
            title=title,
            source_url=source_url,
            apply_url=source_url,
            description=n.strip_html(raw.get("description") or raw.get("jobDescription")),
            location=str(location) if location else None,
            city=city,
            country_code=country_code,
            remote_type=n.detect_remote_type(
                str(location or ""), title, location_data.get("workplaceType")
            ),
            employment_type=n.normalize_employment_type(
                raw.get("employmentType") or raw.get("jobType") or title
            ),
            department=department,
            seniority=n.infer_seniority(title),
            posted_at=_parse_dt(raw.get("postedAt") or raw.get("createdAt")),
            raw_hash=n.compute_raw_hash(raw),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_jobs(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Try known paths in __NEXT_DATA__; fall back to recursive search."""
    for path in _JOB_LIST_PATHS:
        node: Any = data
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = None
                break
        if isinstance(node, list):
            return node

    # Recursive fallback: find the first list whose items look like jobs
    return _find_job_list(data)


def _find_job_list(node: Any, depth: int = 0) -> list[dict[str, Any]] | None:
    """Recursively search for a list of recognizable job records."""
    if depth > 10:
        return None
    if isinstance(node, list):
        if node and isinstance(node[0], dict):
            first = node[0]
            if "title" in first:
                return node
            has_name = any(first.get(key) for key in ("name", "jobTitle"))
            has_id = any(first.get(key) for key in ("id", "jobId", "slug"))
            has_url = any(first.get(key) for key in ("url", "link", "path"))
            if has_name and has_id and has_url:
                return node
        for value in node:
            result = _find_job_list(value, depth + 1)
            if result is not None:
                return result
    if isinstance(node, dict):
        for value in node.values():
            result = _find_job_list(value, depth + 1)
            if result is not None:
                return result
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
