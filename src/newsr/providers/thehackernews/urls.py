from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


THN_ROOT = "https://thehackernews.com"
_ALLOWED_HOSTS = {"thehackernews.com", "www.thehackernews.com"}
_ARTICLE_PATH_RE = re.compile(r"^/\d{4}/\d{2}/[^/]+\.html$")


def normalize_url(href: str) -> str:
    absolute_url = urljoin(THN_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse(("https", host, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(parsed.path))


def article_id_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if path.endswith(".html"):
        return path[:-5]
    return path
