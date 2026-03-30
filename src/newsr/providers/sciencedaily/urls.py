from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


SCIENCEDAILY_ROOT = "https://www.sciencedaily.com"
_ALLOWED_HOSTS = {"sciencedaily.com", "www.sciencedaily.com"}
_ARTICLE_PATH_RE = re.compile(r"^/releases/\d{4}/\d{2}/\d+\.htm$")


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
    absolute_url = urljoin(SCIENCEDAILY_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    path = parsed.path or "/"
    if _ARTICLE_PATH_RE.fullmatch(path):
        normalized_path = path
    else:
        normalized_path = normalize_target_path(path)
    return urlunparse(("https", "www.sciencedaily.com", normalized_path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(parsed.path or ""))


def article_id_from_url(url: str) -> str:
    path = urlparse(normalize_url(url)).path.lstrip("/")
    return path.removesuffix(".htm")
