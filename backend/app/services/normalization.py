"""Pure functions that turn messy source data into the platform's standard shape."""
import hashlib
import html
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TAG_RE = re.compile(r"<[^>]+>")
_BLOCK_RE = re.compile(r"</?(p|div|br|li|ul|ol|h[1-6]|tr|table)\b[^>]*>", re.I)
_WS_RE = re.compile(r"[ \t\r\f\v]+")

_COMPANY_SUFFIXES = {
    "inc", "incorporated", "ltd", "limited", "llc", "gmbh", "bv", "nv",
    "corp", "corporation", "co", "plc", "sa", "ag",
}

# Names plus unambiguous codes only ("CA" is deliberately absent: US state vs Canada).
_COUNTRIES = {
    "netherlands": "NL", "the netherlands": "NL", "nl": "NL",
    "united states": "US", "united states of america": "US", "usa": "US", "us": "US",
    "united kingdom": "GB", "uk": "GB", "gb": "GB", "england": "GB",
    "germany": "DE", "deutschland": "DE", "de": "DE",
    "france": "FR", "fr": "FR", "spain": "ES", "es": "ES", "italy": "IT", "portugal": "PT",
    "ireland": "IE", "belgium": "BE", "switzerland": "CH", "austria": "AT",
    "sweden": "SE", "denmark": "DK", "norway": "NO", "finland": "FI", "poland": "PL",
    "canada": "CA", "australia": "AU", "india": "IN", "singapore": "SG", "japan": "JP",
    "brazil": "BR", "mexico": "MX", "israel": "IL", "united arab emirates": "AE",
}

_TRACKING_PARAMS = {"gh_src", "ref", "source", "src", "fbclid", "gclid", "lever-source"}


def strip_html(value: str | None) -> str | None:
    """Greenhouse returns HTML that is itself entity-escaped, hence the double unescape."""
    if not value:
        return None
    text = html.unescape(value)
    text = _BLOCK_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = (_WS_RE.sub(" ", line).strip() for line in text.splitlines())
    result = "\n".join(line for line in lines if line)
    return result or None


def normalize_company_name(name: str) -> str:
    s = name.lower().replace(".", "").replace("&", " and ")
    s = re.sub(r"[^\w\s]", " ", s)
    tokens = s.split()
    while len(tokens) > 1 and tokens[-1] in _COMPANY_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def normalize_title(title: str) -> str:
    s = title.lower()
    s = re.sub(r"\((?:[mfdwx]\s*[/|]\s*)+[mfdwx]\)", " ", s)  # (m/f/d), (m/w/x)
    s = re.sub(r"\bsr\b\.?", "senior", s)
    s = re.sub(r"\bjr\b\.?", "junior", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_employment_type(text: str | None) -> str | None:
    if not text:
        return None
    s = text.lower()
    if re.search(r"\bintern(ship)?\b", s):
        return "INTERNSHIP"
    if re.search(r"part[\s_-]?time", s):
        return "PART_TIME"
    if re.search(r"full[\s_-]?time|permanent", s):
        return "FULL_TIME"
    if re.search(r"contract|freelance|fixed[\s-]term", s):
        return "CONTRACT"
    if re.search(r"\btemp(orary)?\b", s):
        return "TEMPORARY"
    return None


def detect_remote_type(*texts: str | None) -> str | None:
    s = " ".join(t for t in texts if t).lower()
    if "hybrid" in s:
        return "HYBRID"
    if re.search(r"\bremote\b|work from home|\banywhere\b", s):
        return "REMOTE"
    if re.search(r"on[\s-]?site", s):
        return "ONSITE"
    return None


def infer_seniority(title: str) -> str | None:
    s = normalize_title(title)
    rules = [
        (r"\bintern(ship)?\b", "INTERN"),
        (r"\b(junior|entry|graduate|trainee)\b", "JUNIOR"),
        (r"\bprincipal\b", "PRINCIPAL"),
        (r"\bstaff\b", "STAFF"),
        (r"\b(senior|sr)\b", "SENIOR"),
        (r"\blead\b", "LEAD"),
        (r"\b(manager|head of|director|vp|vice president)\b", "MANAGEMENT"),
    ]
    for pattern, label in rules:
        if re.search(pattern, s):
            return label
    return None


def parse_location(text: str | None) -> tuple[str | None, str | None]:
    """Return (city, ISO country code). Either may be None."""
    if not text:
        return None, None
    parts = [p.strip() for p in re.split(r"[,;/|]| - ", text) if p.strip()]
    country = next((_COUNTRIES[p.lower()] for p in reversed(parts) if p.lower() in _COUNTRIES), None)
    city = next(
        (
            p for p in parts
            if p.lower() not in _COUNTRIES and "remote" not in p.lower() and "hybrid" not in p.lower()
        ),
        None,
    )
    return city, country


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def compute_raw_hash(payload: dict) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def quality_score(
    *, title: str | None, company: str | None, apply_url: str | None,
    location: str | None, description: str | None, has_salary: bool = False,
) -> int:
    """0-100. Weights follow the design doc: 20/20/20/15/15/10."""
    return (
        (20 if title else 0)
        + (20 if company else 0)
        + (20 if apply_url else 0)
        + (15 if location else 0)
        + (15 if description and len(description) >= 200 else 0)
        + (10 if has_salary else 0)
    )
