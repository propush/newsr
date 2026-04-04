from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


NINE_TO_FIVE_MAC_ROOT = "https://9to5mac.com"
_ALLOWED_HOSTS = {"9to5mac.com", "www.9to5mac.com"}
_ARTICLE_PATH_RE = re.compile(r"^/\d{4}/\d{2}/\d{2}/[^/]+/$")


def normalize_target_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return "/"
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    if stripped == "/":
        return stripped
    return f"{stripped.rstrip('/')}/"


def normalize_url(href: str) -> str:
    absolute_url = urljoin(NINE_TO_FIVE_MAC_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    path = normalize_target_path(parsed.path or "/")
    host = parsed.netloc.lower()
    if host in _ALLOWED_HOSTS or not host:
        host = "9to5mac.com"
    return urlunparse(("https", host, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(parsed.path or ""))


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")
