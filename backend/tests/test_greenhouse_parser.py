import pytest

from app.connectors.greenhouse import GreenhouseConnector

RAW = {
    "id": 4567890,
    "title": "Senior QA Automation Engineer",
    "absolute_url": "https://boards.greenhouse.io/example/jobs/4567890?gh_src=abc",
    "location": {"name": "Amsterdam, Netherlands"},
    "first_published": "2026-10-20T09:15:00-04:00",
    "updated_at": "2026-11-01T10:00:00-04:00",
    "departments": [{"name": "Engineering"}],
    "content": "&lt;p&gt;Build test automation with Playwright &amp;amp; Python.&lt;/p&gt;",
}


@pytest.fixture
def connector():
    return GreenhouseConnector({"board_token": "example"})


def test_parse_job(connector):
    job = connector.parse_job(RAW)
    assert job.external_id == "4567890"
    assert job.title == "Senior QA Automation Engineer"
    assert job.source_url == "https://boards.greenhouse.io/example/jobs/4567890"
    assert (job.city, job.country_code) == ("Amsterdam", "NL")
    assert job.seniority == "SENIOR"
    assert job.department == "Engineering"
    assert job.description == "Build test automation with Playwright & Python."
    assert job.posted_at is not None and job.posted_at.year == 2026
    assert len(job.raw_hash) == 64


def test_parse_rejects_incomplete_record(connector):
    with pytest.raises(ValueError):
        connector.parse_job({"id": 1, "title": "No URL"})


def test_config_validation():
    GreenhouseConnector.validate_config({"board_token": "airbnb"})
    with pytest.raises(ValueError):
        GreenhouseConnector.validate_config({})
    with pytest.raises(ValueError):
        GreenhouseConnector.validate_config({"board_token": "../etc"})
