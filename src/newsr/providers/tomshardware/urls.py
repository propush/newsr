from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


TOMSHARDWARE_ROOT = "https://www.tomshardware.com"
_ALLOWED_HOSTS = {"tomshardware.com", "www.tomshardware.com"}
_BLOCKED_PREFIXES = (
    "/best-picks",
    "/coupons",
    "/deals",
    "/pro",
    "/tag/",
)
_TARGET_PATHS = {
    "/pc-components",
    "/pc-components/cpus",
    "/pc-components/gpus",
    "/pc-components/storage",
    "/laptops/news",
    "/desktops",
    "/software",
    "/tech-industry/artificial-intelligence",
}


def normalize_url(href: str) -> str:
    absolute_url = urljoin(TOMSHARDWARE_ROOT, href.strip())
    parsed = urlparse(absolute_url)
    host = parsed.netloc.lower()
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = f"/{path}"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return urlunparse(("https", host, path, "", "", ""))


def normalize_target_path(path: str) -> str:
    return urlparse(normalize_url(path)).path or "/"


def is_article_url(url: str) -> bool:
    parsed = urlparse(normalize_url(url))
    if parsed.netloc.lower() not in _ALLOWED_HOSTS:
        return False
    path = parsed.path or "/"
    if path in _TARGET_PATHS or path == "/":
        return False
    if any(path.startswith(prefix) for prefix in _BLOCKED_PREFIXES):
        return False
    if path.startswith("/reviews/"):
        slug = path.rsplit("/", 1)[-1]
        return slug.endswith(".html") and "best-" not in slug
    if (
        path.startswith("/pc-components/")
        or path.startswith("/laptops/")
        or path.startswith("/desktops/")
        or path.startswith("/software/")
        or path.startswith("/tech-industry/artificial-intelligence/")
    ):
        segments = [segment for segment in path.strip("/").split("/") if segment]
        if len(segments) < 2:
            return False
        blocked = {"best-picks", "deals", "gallery", "galleries"}
        return not any(segment in blocked for segment in segments)
    return False


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")
