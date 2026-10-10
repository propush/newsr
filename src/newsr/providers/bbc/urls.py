from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse


BBC_ROOT = "https://www.bbc.com"
_CATEGORY_EXCLUDE = {"articles", "av", "future", "in_pictures", "live", "topics"}
_SECTION_SLUGS = {
    "/news": "latest",
    "/technology": "technology",
    "/business": "business",
    "/health": "health",
    "/culture/entertainment-news": "entertainment_and_arts",
    "/culture": "culture",
    "/arts": "arts",
    "/travel": "travel",
    "/future-planet": "earth",
    "/news/science_and_environment": "science-environment",
}
_FEATURE_ARTICLE_RE = re.compile(r"^/(?:future|culture|travel|worklife|earth|innovation|arts)/article/[^/]+$")


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk"}:
        return False
    path = parsed.path.rstrip("/")
    if _FEATURE_ARTICLE_RE.fullmatch(path):
        return True
    if not path.startswith("/news/"):
        return False
    if path.startswith("/news/live/"):
        return False
    if path.startswith("/news/topics/"):
        return False

    slug = path.split("/")[-1]
    if not slug:
        return False
    if path.startswith("/news/articles/"):
        return len(path.strip("/").split("/")) == 3
    return len(path.strip("/").split("/")) == 2 and bool(re.search(r"-\d+$", slug))


def normalize_url(href: str) -> str:
    return urljoin(BBC_ROOT, href.split("?")[0])


def article_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] or path.replace("/", "_")


def category_slug_from_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk"}:
        return None
    path = parsed.path.rstrip("/")
    if path in _SECTION_SLUGS:
        return _SECTION_SLUGS[path]
    parts = [part for part in path.split("/") if part]
    if len(parts) not in {2, 3} or parts[0] != "news":
        return None
    if any(part in _CATEGORY_EXCLUDE for part in parts[1:]):
        return None
    if not all(part.replace("_", "").replace("-", "").isalpha() for part in parts[1:]):
        return None
    return "/".join(parts[1:])


def label_from_slug(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()
