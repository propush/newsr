from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


DELOITTE_ROOT = "https://www.deloitte.com"
DELOITTE_SEARCH_ENDPOINT = f"{DELOITTE_ROOT}/modern-prod-english/_search"
_ALLOWED_HOSTS = {"deloitte.com", "www.deloitte.com"}
_DUPLICATE_HTML_SUFFIX_RE = re.compile(r"(?:\.html)+$")


def normalize_target_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return "/"
    absolute_url = urljoin(DELOITTE_ROOT, stripped)
    parsed = urlparse(absolute_url)
    normalized_path = _normalize_path(parsed.path or "/")
    return normalized_path


def normalize_url(href: str) -> str:
    absolute_url = urljoin(DELOITTE_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower() or "www.deloitte.com"
    path = _normalize_path(parsed.path or "/")
    return urlunparse(("https", host, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    if not parsed.path.startswith("/us/en/insights/"):
        return False
    if not parsed.path.endswith(".html"):
        return False
    if "/multimedia/" in parsed.path:
        return False
    blocked_paths = {
        "/us/en/insights.html",
        "/us/en/insights/topics.html",
        "/us/en/insights/industry.html",
        "/us/en/insights/research-centers.html",
    }
    return parsed.path not in blocked_paths


def is_research_hub_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return parsed.path.startswith("/us/en/insights/research-centers/") and parsed.path.endswith(".html")


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")


def _normalize_path(path: str) -> str:
    normalized = path if path.startswith("/") else f"/{path}"
    if normalized.endswith(".html.html"):
        normalized = _DUPLICATE_HTML_SUFFIX_RE.sub(".html", normalized)
    elif normalized.endswith("/") and normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized
