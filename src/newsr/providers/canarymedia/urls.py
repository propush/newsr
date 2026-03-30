from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


CANARYMEDIA_ROOT = "https://www.canarymedia.com"
_ALLOWED_HOSTS = {"canarymedia.com", "www.canarymedia.com"}
_ARTICLE_PATH_RE = re.compile(r"^/articles/[^/]+/[^/]+/?$")
_PAGINATION_SEGMENT_RE = re.compile(r"^p\d+$")
_REJECTED_SECTION_SLUGS = {"sponsored"}


def normalize_target_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return "/"
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    if len(stripped) > 1 and stripped.endswith("/"):
        stripped = stripped[:-1]
    return stripped or "/"


def normalize_url(href: str) -> str:
    absolute_url = urljoin(CANARYMEDIA_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path = normalize_target_path(parsed.path or "/")
    return urlunparse(("https", host, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    path = normalize_target_path(parsed.path or "/")
    if not _ARTICLE_PATH_RE.fullmatch(path):
        return False
    segments = [segment for segment in path.split("/") if segment]
    return (
        len(segments) == 3
        and segments[1] not in _REJECTED_SECTION_SLUGS
        and not _PAGINATION_SEGMENT_RE.fullmatch(segments[2])
    )


def article_id_from_url(url: str) -> str:
    return normalize_target_path(urlparse(url).path or "/").lstrip("/")
