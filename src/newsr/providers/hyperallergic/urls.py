from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse


HYPERALLERGIC_ROOT = "https://hyperallergic.com"
_ALLOWED_HOSTS = {"hyperallergic.com", "www.hyperallergic.com"}
_BLOCKED_PREFIXES = (
    "/about/",
    "/advertise/",
    "/author/",
    "/category/",
    "/contact/",
    "/donate/",
    "/jobs/",
    "/member-faq/",
    "/newsletters/",
    "/page/",
    "/privacy-policy/",
    "/tag/",
)
_BLOCKED_SLUGS = {
    "about",
    "advertise",
    "contact",
    "donate",
    "jobs",
    "member-faq",
    "newsletters",
    "privacy-policy",
}


def normalize_url(href: str) -> str:
    absolute_url = urljoin(HYPERALLERGIC_ROOT, href.strip())
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
    path = parsed.path or "/"
    if path == "/":
        return False
    if any(path.startswith(prefix) for prefix in _BLOCKED_PREFIXES):
        return False
    slug = path.strip("/")
    if not slug or "/" in slug or slug in _BLOCKED_SLUGS:
        return False
    return True


def article_id_from_url(url: str) -> str:
    return urlparse(normalize_url(url)).path.strip("/")
