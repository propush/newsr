from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


HRDIVE_ROOT = "https://www.hrdive.com"
_ALLOWED_HOSTS = {"hrdive.com", "www.hrdive.com"}
_ARTICLE_PATH_RE = re.compile(r"^/news/[^/]+/\d+/?$")


def normalize_target_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return "/"
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    if stripped != "/" and not stripped.endswith("/"):
        stripped = f"{stripped}/"
    return stripped


def normalize_url(href: str) -> str:
    absolute_url = urljoin(HRDIVE_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path = normalize_target_path(parsed.path or "/")
    return urlunparse(("https", host, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(parsed.path))


def article_id_from_url(url: str) -> str:
    return urlparse(url).path.strip("/")
