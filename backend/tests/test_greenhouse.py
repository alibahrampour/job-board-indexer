import pytest
from pydantic import ValidationError

from app.connectors.greenhouse import GreenhouseConnector
from app.services.pipeline import normalize_parsed

RAW = {
    "id": 4012345,
    "title": "Senior QA Automation Engineer",
    "absolute_url": "https://boards.greenhouse.io/acme/jobs/4012345",
    "location": {"name": "Amsterdam, Netherlands (Hybrid)"},
    "updated_at": "2026-11-01T10:15:00-05:00",
    "content": "&lt;p&gt;Build test automation with &lt;b&gt;Playwright&lt;/b&gt;.&lt;/p&gt;",
    "departments": [{"name": "Engineering"}],
}


def make():
    return GreenhouseConnector(config={"board_token": "acme", "company_name": "Acme B.V."})


def test_parse_job():
    parsed = make().parse_job(RAW)
    assert parsed.external_id == "4012345"
    assert parsed.company_name == "Acme B.V."
    assert parsed.department == "Engineering"
    assert parsed.posted_at is not None


def test_normalize_parsed():
    fields = normalize_parsed(make().parse_job(RAW))
    assert fields["seniority"] == "SENIOR"
    assert fields["remote_type"] == "HYBRID"
    assert fields["city"] == "Amsterdam"
    assert fields["country_code"] == "NL"
    assert "Playwright" in fields["description"]


def test_missing_title_is_rejected():
    with pytest.raises(ValidationError):
        make().parse_job({**RAW, "title": ""})


def test_missing_url_is_rejected():
    bad = {k: v for k, v in RAW.items() if k != "absolute_url"}
    with pytest.raises(ValidationError):
        make().parse_job(bad)
