import asyncio
import json

import pytest

from app.connectors.ashby import AshbyConnector
from app.connectors.bamboohr import BambooHRConnector
from app.connectors.base import ConnectorError
from app.connectors.breezy import BreezyConnector
from app.connectors.greenhouse import GreenhouseConnector
from app.connectors.lever import LeverConnector
from app.connectors.personio import PersonioConnector
from app.connectors.pinpoint import PinpointConnector
from app.connectors.recruitee import RecruiteeConnector
from app.connectors.rippling import RipplingConnector
from app.connectors.smartrecruiters import SmartRecruitersConnector
from app.connectors.teamtailor import TeamtailorConnector
from app.connectors.workable import WorkableConnector
from app.connectors.workday import WorkdayConnector
from app.connectors.wp_job_manager import WPJobManagerConnector


CASES = [
    (
        GreenhouseConnector,
        {"board_token": "acme"},
        {
            "id": 101, "title": "QA Engineer",
            "absolute_url": "https://boards.greenhouse.io/acme/jobs/101",
            "location": {"name": "Amsterdam, Netherlands"},
        },
        "101", "https://boards.greenhouse.io/acme/jobs/101",
    ),
    (
        AshbyConnector,
        {"board": "acme"},
        {"id": "ashby-1", "title": "QA Engineer", "jobUrl": "https://jobs.ashbyhq.com/acme/1"},
        "ashby-1", "https://jobs.ashbyhq.com/acme/1",
    ),
    (
        BambooHRConnector,
        {"company": "acme"},
        {"id": 102, "jobOpeningName": "QA Engineer"},
        "102", "https://acme.bamboohr.com/careers/102",
    ),
    (
        BreezyConnector,
        {"company": "acme"},
        {"_id": "breezy-1", "name": "QA Engineer"},
        "breezy-1", "https://acme.breezy.hr/p/breezy-1",
    ),
    (
        LeverConnector,
        {"company": "acme"},
        {"id": "lever-1", "text": "QA Engineer", "hostedUrl": "https://jobs.lever.co/acme/1"},
        "lever-1", "https://jobs.lever.co/acme/1",
    ),
    (
        PersonioConnector,
        {"tenant": "acme"},
        {"id": "personio-1", "attributes": {"name": "QA Engineer"}},
        "personio-1", "https://acme.jobs.personio.de/personio-1",
    ),
    (
        PinpointConnector,
        {"tenant": "acme"},
        {"id": "pinpoint-1", "title": "QA Engineer"},
        "pinpoint-1", "https://acme.pinpointhq.com/postings/pinpoint-1",
    ),
    (
        RecruiteeConnector,
        {"tenant": "acme"},
        {
            "id": "recruitee-1", "title": "QA Engineer",
            "careers_url": "https://acme.recruitee.com/o/qa-engineer",
        },
        "recruitee-1", "https://acme.recruitee.com/o/qa-engineer",
    ),
    (
        RipplingConnector,
        {"company": "acme"},
        {"id": "rippling-1", "title": "QA Engineer", "url": "/jobs/qa-engineer"},
        "rippling-1", "https://ats.rippling.com/acme/jobs/qa-engineer",
    ),
    (
        SmartRecruitersConnector,
        {"company_id": "acme"},
        {"id": "smart-1", "name": "QA Engineer"},
        "smart-1", "https://jobs.smartrecruiters.com/acme/smart-1",
    ),
    (
        TeamtailorConnector,
        {"tenant": "acme"},
        {
            "_id": "teamtailor-1", "_title": "QA Engineer",
            "_link": "https://acme.teamtailor.com/jobs/1",
        },
        "teamtailor-1", "https://acme.teamtailor.com/jobs/1",
    ),
    (
        WorkableConnector,
        {"subdomain": "acme"},
        {"shortcode": "workable-1", "title": "QA Engineer"},
        "workable-1", "https://apply.workable.com/acme/j/workable-1",
    ),
    (
        WorkdayConnector,
        {"tenant": "acme", "site": "Acme_Careers"},
        {"title": "QA Engineer", "externalPath": "/job/QA_Engineer", "bulletFields": ["wd-1"]},
        "wd-1", "https://acme.wd1.myworkdayjobs.com/job/QA_Engineer",
    ),
    (
        WPJobManagerConnector,
        {"feed_url": "https://jobs.example.com/?feed=job_feed"},
        {
            "_id": "wp-1", "_title": "QA Engineer",
            "_link": "https://jobs.example.com/job/qa-engineer",
            "_company": "Example Corp",
        },
        "wp-1", "https://jobs.example.com/job/qa-engineer",
    ),
]


@pytest.mark.parametrize("connector_class,config,raw,external_id,url", CASES)
def test_native_connector_config_and_job_parsing(connector_class, config, raw, external_id, url):
    connector_class.validate_config(config)
    assert connector_class.build_base_url(config)
    parsed = connector_class(config).parse_job(raw)
    assert parsed.external_id == external_id
    assert parsed.title.casefold() == "qa engineer"
    assert parsed.source_url == url
    assert len(parsed.raw_hash) == 64


@pytest.mark.parametrize("connector_class,config", [
    (GreenhouseConnector, {"board_token": "acme"}),
    (AshbyConnector, {"board": "acme"}),
    (BambooHRConnector, {"company": "acme"}),
    (BreezyConnector, {"company": "acme"}),
    (LeverConnector, {"company": "acme"}),
    (PersonioConnector, {"tenant": "acme"}),
    (PinpointConnector, {"tenant": "acme"}),
    (RecruiteeConnector, {"tenant": "acme"}),
    (RipplingConnector, {"company": "acme"}),
    (SmartRecruitersConnector, {"company_id": "acme"}),
    (TeamtailorConnector, {"tenant": "acme"}),
    (WorkableConnector, {"subdomain": "acme"}),
    (WorkdayConnector, {"tenant": "acme"}),
    (WPJobManagerConnector, {"feed_url": "https://jobs.example.com/?feed=job_feed"}),
])
def test_native_connector_fetch_contract(connector_class, config, monkeypatch):
    connector = connector_class(config)

    async def get_json(url, params=None):
        if connector_class is GreenhouseConnector:
            return {"jobs": []}
        if connector_class is AshbyConnector:
            return {"jobs": []}
        if connector_class is BambooHRConnector:
            return {"result": []}
        if connector_class is BreezyConnector:
            return []
        if connector_class is LeverConnector:
            return []
        if connector_class is PersonioConnector:
            return {"data": []}
        if connector_class is PinpointConnector:
            return []
        if connector_class is RecruiteeConnector:
            return {"offers": []}
        if connector_class is SmartRecruitersConnector:
            return {"content": []}
        if connector_class is WorkableConnector:
            return {"results": [], "hasMore": False}
        if connector_class is WorkdayConnector:
            return {"jobPostings": [], "total": 0}
        raise AssertionError(f"Unexpected JSON request: {url}")

    async def get_text(url):
        return """<rss version="2.0"><channel><item><title>QA Engineer</title></item></channel></rss>"""

    async def get_html(url):
        return '<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"jobs":[{"title":"QA Engineer"}]}}}</script>'

    async def post_json(url, body):
        return {"jobPostings": [], "total": 0}

    class Response:
        status_code = 200
        is_success = True
        text = json.dumps({"data": []})

        def json(self):
            return {"data": []}

    class Client:
        async def get(self, url, headers=None):
            return Response()

    monkeypatch.setattr(connector, "_get_json", get_json)
    monkeypatch.setattr(connector, "_get_text", get_text, raising=False)
    monkeypatch.setattr(connector, "_get_html", get_html, raising=False)
    monkeypatch.setattr(connector, "_post_json", post_json, raising=False)
    if connector_class is PersonioConnector:
        connector._client = Client()
    jobs = asyncio.run(connector.fetch_jobs())
    assert isinstance(jobs, list)
    assert all(isinstance(job, dict) for job in jobs)


def test_rippling_empty_job_board_is_reported_as_fetch_error(monkeypatch):
    connector = RipplingConnector({"company": "acme"})

    async def get_html(url):
        return "<html><body>No structured job data</body></html>"

    monkeypatch.setattr(connector, "_get_html", get_html)
    with pytest.raises(ConnectorError, match="Could not find job data"):
        asyncio.run(connector.fetch_jobs())


def test_pinpoint_parses_live_nested_location_and_posting_url():
    connector = PinpointConnector({"tenant": "bluemantis"})
    parsed = connector.parse_job({
        "id": "536384",
        "title": "Azure FinOps Consultant - PR",
        "url": "https://bluemantis.pinpointhq.com/en/postings/536384",
        "location": {"name": "Remote", "city": "", "province": ""},
        "employment_type": "full_time",
        "description": "<p>Cloud FinOps role</p>",
    })

    assert parsed.source_url == "https://bluemantis.pinpointhq.com/en/postings/536384"
    assert parsed.location == "Remote"
    assert parsed.remote_type == "REMOTE"
    assert parsed.employment_type == "FULL_TIME"
    assert parsed.description == "Cloud FinOps role"


def test_rippling_extracts_and_parses_live_job_listing_shape(monkeypatch):
    connector = RipplingConnector({"company": "arine"})
    page_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [{
                        "state": {
                            "data": {
                                "items": [{
                                    "id": "job-1",
                                    "name": "Client Success Executive",
                                    "url": "https://ats.rippling.com/arine/jobs/job-1",
                                    "department": {"name": "Commercial"},
                                    "locations": [{
                                        "name": "Remote (United States of America)",
                                        "countryCode": "US",
                                        "workplaceType": "REMOTE",
                                    }],
                                }]
                            }
                        }
                    }]
                }
            }
        }
    }

    async def get_html(url):
        return (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(page_data)
            + "</script>"
        )

    monkeypatch.setattr(connector, "_get_html", get_html)
    jobs = asyncio.run(connector.fetch_jobs())
    parsed = connector.parse_job(jobs[0])

    assert parsed.external_id == "job-1"
    assert parsed.title == "Client Success Executive"
    assert parsed.department == "Commercial"
    assert parsed.location == "Remote (United States of America)"
    assert parsed.country_code == "US"
    assert parsed.remote_type == "REMOTE"
