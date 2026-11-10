import asyncio
import csv
import re
from pathlib import Path

import pytest

from app.connectors.base import ConnectorError
from app.connectors.registry import CONNECTORS, get_connector_class
from app.connectors.unavailable import UnavailablePlatformConnector


ROOT = Path(__file__).resolve().parents[1]
KEY_OVERRIDES = {
    "Breezy HR": "breezy",
    "Greenhouse": "greenhouse",
    "Lever.co": "lever",
    "WP Job Manager": "wp_job_manager",
}


def _key(name: str) -> str:
    return KEY_OVERRIDES.get(name) or re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def test_every_platform_has_its_own_registered_connector_class():
    with (ROOT / "data" / "platforms.csv").open(encoding="utf-8", newline="") as file:
        platforms = list(csv.DictReader(file))

    expected_keys = {_key(row["name"]) for row in platforms}
    assert len(platforms) == 78
    assert set(CONNECTORS) == expected_keys
    assert len({id(cls) for cls in CONNECTORS.values()}) == 78

    for row in platforms:
        connector = get_connector_class(_key(row["name"]))
        assert connector.platform_type == row["category"]
        if issubclass(connector, UnavailablePlatformConnector):
            assert connector.platform_name == row["name"]


def test_unimplemented_connector_refuses_registration_and_fetch():
    connector_class = get_connector_class("adp")
    assert issubclass(connector_class, UnavailablePlatformConnector)

    with pytest.raises(ValueError, match="no verified connector implementation"):
        connector_class.validate_config({"jobs_url": "https://example.com/jobs"})

    with pytest.raises(ConnectorError, match="not implemented"):
        asyncio.run(connector_class({}).fetch_jobs())


def test_known_platform_uses_its_native_connector():
    assert get_connector_class("greenhouse").__name__ == "GreenhouseConnector"
