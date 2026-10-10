from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

from .catalog import BASE_TARGET_OPTIONS

TOMSHARDWARE_ROOT = "https://www.tomshardware.com"
_ALLOWED_HOSTS = {"tomshardware.com", "www.tomshardware.com"}
_BLOCKED_PREFIXES = (
    "/best-picks",
    "/coupons",
    "/deals",
    "/pro",
    "/tag/",
)
_TARGET_PATHS = {"/news"} | {
    path
    for option in BASE_TARGET_OPTIONS
    for path in (option.path, option.path.removesuffix("/news"))
}
_ARTICLE_PREFIXES = (
    "/pc-components/", "/laptops/", "/desktops/", "/software/",
    "/tech-industry/", "/networking/", "/monitors/", "/peripherals/", "/3d-printing/",
)


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
    if path.startswith("/news/"):
        return path.endswith(".html") and len(path.strip("/").split("/")) == 2
    if path.startswith(_ARTICLE_PREFIXES):
        segments = [segment for segment in path.strip("/").split("/") if segment]
        if len(segments) < 2:
            return False
        blocked = {"best-picks", "deals", "gallery", "galleries"}
        if segments[-1] in {"news", "reviews"}:
            return False
        return not any(segment in blocked for segment in segments)
    return False


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")
