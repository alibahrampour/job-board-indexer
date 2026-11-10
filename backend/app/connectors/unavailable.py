"""Base behavior for registered platforms awaiting a verified implementation."""
from typing import Any

from app.connectors.base import BaseConnector, ConnectorError, NormalizedJob


class UnavailablePlatformConnector(BaseConnector):
    """Explicitly unavailable connector; it never pretends to crawl a platform."""

    key = ""
    platform_name = ""
    platform_type = "ATS"
    connector_type = "unsupported"
    family = ""

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> None:
        raise ValueError(
            f"{cls.platform_name} is catalogued but has no verified connector implementation"
        )

    async def fetch_jobs(self) -> list[dict[str, Any]]:
        raise ConnectorError(
            f"{self.platform_name} connector is not implemented; no jobs were fetched",
            permanent=True,
        )

    def parse_job(self, raw_job: dict[str, Any]) -> NormalizedJob:
        raise ConnectorError(
            f"{self.platform_name} connector is not implemented",
            permanent=True,
        )

    async def health_check(self) -> bool:
        return False
