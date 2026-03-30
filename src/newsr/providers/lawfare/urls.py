from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse


LAWFARE_ROOT = "https://www.lawfaremedia.org"
_CANONICAL_HOST = "www.lawfaremedia.org"
_ALLOWED_HOSTS = {"lawfaremedia.org", "www.lawfaremedia.org"}
_ARTICLE_PATH_RE = re.compile(r"^/article/[^/]+/?$")


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
    absolute_url = urljoin(LAWFARE_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    path = normalize_target_path(parsed.path or "/")
    return urlunparse(("https", _CANONICAL_HOST, path, "", "", ""))


def is_article_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    return bool(_ARTICLE_PATH_RE.fullmatch(normalize_target_path(parsed.path or "/")))


def article_id_from_url(url: str) -> str:
    path = normalize_target_path(urlparse(url).path or "/")
    return path.removeprefix("/article/").strip("/")
