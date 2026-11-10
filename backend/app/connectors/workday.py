import asyncio
import hashlib
from datetime import datetime
from typing import Any

import httpx

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob
from app.services import normalization as n

_PAGE_SIZE = 20


class WorkdayConnector(BaseConnector):
    """Workday ATS — POST-based paginated job search API."""

    key = "workday"
    platform_type = "ATS"
    connector_type = "api"

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        if not (config.get("tenant") or "").strip():
            raise ValueError("config.tenant is required")

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str:
        tenant = config["tenant"]
        instance = config.get("instance") or "1"
        return f"https://{tenant}.wd{instance}.myworkdayjobs.com"

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    @property
    def _tenant(self) -> str:
        return self.config["tenant"]

    @property
    def _instance(self) -> str:
        return str(self.config.get("instance") or "1")

    @property
    def _site(self) -> str:
        return self.config.get("site") or f"{self._tenant}_External_Career_Site"

    @property
    def _base(self) -> str:
        return f"https://{self._tenant}.wd{self._instance}.myworkdayjobs.com"

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _post_json(self, url: str, body: dict[str, Any]) -> Any:
        """POST *url* with *body* as JSON; retries on transient errors."""
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        last_error = "unknown error"
        for delay in self.RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await self._client.post(
                    url,
                    json=body,
                    headers={"Content-Type": "application/json"},
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
                return resp.json()
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ConnectorError(f"bad response from {url}: {exc}") from exc
        raise ConnectorError(f"gave up after retries ({last_error}) for {url}")

    # ------------------------------------------------------------------
    # Connector contract
    # ------------------------------------------------------------------

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        api_url = (
            f"{self._base}/wday/cxs/{self._tenant}/{self._site}/jobs"
        )
        all_jobs: list[dict[str, Any]] = []
        offset = 0

        while True:
            body = {
                "limit": _PAGE_SIZE,
                "offset": offset,
                "searchText": "",
                "appliedFacets": {},
            }
            data = await self._post_json(api_url, body)
            if not isinstance(data, dict):
                raise ConnectorError("unexpected Workday response shape (not a dict)")

            page = data.get("jobPostings")
            if not isinstance(page, list) or not all(isinstance(job, dict) for job in page):
                raise ConnectorError(
                    "unexpected Workday response shape (expected a 'jobPostings' list of jobs)"
                )

            all_jobs.extend(page)

            total = data.get("total", 0)
            offset += len(page)
            if offset >= total or not page:
                break

        return all_jobs

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name") or self._tenant.replace("-", " ").title()

    async def health_check(self) -> bool:
        try:
            api_url = (
                f"{self._base}/wday/cxs/{self._tenant}/{self._site}/jobs"
            )
            await self._post_json(
                api_url,
                {"limit": 1, "offset": 0, "searchText": "", "appliedFacets": {}},
            )
            return True
        except ConnectorError:
            return False

    def parse_job(self, raw: dict[str, Any]) -> NormalizedJob:
        title = (raw.get("title") or "").strip()
        external_path = raw.get("externalPath") or ""

        # Prefer a stable bulletFields ID, fall back to a hash of the path
        bullet = raw.get("bulletFields") or []
        job_id = str(bullet[0]).strip() if bullet else ""
        if not job_id and external_path:
            job_id = hashlib.sha1(external_path.encode()).hexdigest()[:16]

        url = f"{self._base}{external_path}" if external_path else ""

        if not job_id or not title or not url:
            raise ValueError("missing id, title or externalPath in Workday job payload")

        location = raw.get("locationsText") or None
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
            seniority=n.infer_seniority(title),
            posted_at=_parse_workday_date(raw.get("postedOn")),
            raw_hash=n.compute_raw_hash(raw),
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_workday_date(value: str | None) -> datetime | None:
    """Parse Workday's posted date, e.g. '10/01/2026' (MM/DD/YYYY)."""
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None
