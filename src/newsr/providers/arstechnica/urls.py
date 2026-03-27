from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


ARS_ROOT = "https://arstechnica.com"
_ALLOWED_HOSTS = {"arstechnica.com", "www.arstechnica.com"}
_ARTICLE_PATH_RE = re.compile(r"^/[^/]+/\d{4}/\d{2}/[^/]+/$")


def normalize_url(href: str) -> str:
    absolute_url = urljoin(ARS_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path = f"{path}/"
    return urlunparse(("https", host, path, "", "", ""))


def normalize_target_path(path: str) -> str:
    return urlparse(normalize_url(path)).path or "/"


def is_article_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(parsed.path))


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")
