import pytest

from app.services import normalization as n


@pytest.mark.parametrize("raw,expected", [
    ("Full Time", "FULL_TIME"), ("FULL-TIME", "FULL_TIME"), ("full_time", "FULL_TIME"),
    ("Permanent", "FULL_TIME"), ("Part-time", "PART_TIME"), ("Contractor", "CONTRACT"),
    ("Summer Internship", "INTERNSHIP"), ("Internal Tools Engineer", None), (None, None),
])
def test_employment_type(raw, expected):
    assert n.normalize_employment_type(raw) == expected


@pytest.mark.parametrize("raw,expected", [
    ("Amsterdam, Netherlands", ("Amsterdam", "NL")),
    ("Amsterdam, NL", ("Amsterdam", "NL")),
    ("Amsterdam", ("Amsterdam", None)),
    ("Remote - Germany", (None, "DE")),
    ("San Francisco, CA", ("San Francisco", None)),
    ("Berlin, Germany", ("Berlin", "DE")),
    (None, (None, None)),
])
def test_parse_location(raw, expected):
    assert n.parse_location(raw) == expected


def test_remote_detection():
    assert n.detect_remote_type("Amsterdam (Hybrid)") == "HYBRID"
    assert n.detect_remote_type("Remote - EMEA") == "REMOTE"
    assert n.detect_remote_type("Amsterdam") is None


def test_company_and_title_normalization():
    assert n.normalize_company_name("Example B.V.") == "example"
    assert n.normalize_company_name("Acme, Inc.") == "acme"
    assert n.normalize_company_name("Inc") == "inc"
    assert n.normalize_title("Sr. QA Engineer (m/f/d)") == "senior qa engineer"


def test_seniority():
    assert n.infer_seniority("Senior QA Automation Engineer") == "SENIOR"
    assert n.infer_seniority("Software Engineering Intern") == "INTERN"
    assert n.infer_seniority("QA Engineer") is None


def test_canonicalize_url():
    assert n.canonicalize_url("HTTPS://Example.com/jobs/1/?utm_source=x&gh_src=y&id=3#top") == \
        "https://example.com/jobs/1?id=3"


def test_strip_html_handles_escaped_markup():
    assert n.strip_html("&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;&lt;ul&gt;&lt;li&gt;One&lt;/li&gt;&lt;/ul&gt;") == \
        "Hello & welcome\nOne"


def test_raw_hash_is_stable_and_sensitive():
    assert n.compute_raw_hash({"a": 1, "b": 2}) == n.compute_raw_hash({"b": 2, "a": 1})
    assert n.compute_raw_hash({"a": 1}) != n.compute_raw_hash({"a": 2})
