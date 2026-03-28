from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


HBR_ROOT = "https://hbr.org"
_ALLOWED_HOSTS = {"hbr.org", "www.hbr.org"}
_ARTICLE_PATH_RE = re.compile(r"^/\d{4}/\d{2}/[^/]+$")


def normalize_target_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        return "/"
    if not stripped.startswith("/"):
        stripped = f"/{stripped}"
    if stripped != "/":
        stripped = stripped.rstrip("/")
    return stripped


def normalize_url(href: str) -> str:
    absolute_url = urljoin(HBR_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    path = normalize_target_path(parsed.path or "/")
    return urlunparse(("https", "hbr.org", path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(normalize_target_path(parsed.path or "/")))


def article_id_from_url(url: str) -> str:
    return normalize_target_path(urlparse(url).path or "/").strip("/")
