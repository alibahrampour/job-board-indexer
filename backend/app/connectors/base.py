import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import settings


class ConnectorError(Exception):
    """`permanent=True` means retrying will not help (404, 401, bad config)."""

    def __init__(self, message: str, permanent: bool = False):
        super().__init__(message)
        self.permanent = permanent


class NormalizedJob(BaseModel):
    """The standard shape every connector must produce."""

    external_id: str
    title: str
    source_url: str
    apply_url: str | None = None
    company_name: str | None = None  # only for multi-company sources (job boards)
    description: str | None = None
    location: str | None = None
    city: str | None = None
    country_code: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    department: str | None = None
    seniority: str | None = None
    posted_at: datetime | None = None
    raw_hash: str


class BaseConnector(ABC):
    key: str                 # registry key
    platform_type: str       # ATS | JOB_BOARD
    connector_type: str      # api | http | browser
    RETRY_DELAYS = (0, 2, 8)  # seconds before each attempt

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._client: httpx.AsyncClient | None = None

    # --- lifecycle -------------------------------------------------------
    async def __aenter__(self) -> "BaseConnector":
        self._client = httpx.AsyncClient(
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()

    # --- config hooks ----------------------------------------------------
    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        """Raise ValueError when the config is unusable."""

    @classmethod
    def build_base_url(cls, config: dict[str, Any]) -> str | None:
        return None

    # --- contract --------------------------------------------------------
    @abstractmethod
    async def fetch_jobs(self) -> list[dict[str, Any]]:
        """Return raw job payloads. Must raise ConnectorError if the listing is incomplete."""

    @abstractmethod
    def parse_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        """Convert one raw payload into a NormalizedJob. Raise on malformed input."""

    @abstractmethod
    async def health_check(self) -> bool: ...

    async def fetch_company_name(self) -> str | None:
        return self.config.get("company_name")

    # --- shared HTTP helper with backoff ---------------------------------
    async def _get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        if self._client is None:
            raise RuntimeError("Use the connector as `async with connector:`")
        last_error = "unknown error"
        for delay in self.RETRY_DELAYS:
            if delay:
                await asyncio.sleep(delay)
            try:
                resp = await self._client.get(url, params=params)
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
                raise ConnectorError(f"HTTP {resp.status_code} for {url}", permanent=True)
            try:
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPStatusError, ValueError) as exc:
                raise ConnectorError(f"bad response from {url}: {exc}") from exc
        raise ConnectorError(f"gave up after retries ({last_error}) for {url}")
