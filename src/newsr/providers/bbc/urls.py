from __future__ import annotations

from urllib.parse import urljoin, urlparse


BBC_ROOT = "https://www.bbc.com"
_CATEGORY_EXCLUDE = {"articles", "av", "future", "in_pictures", "live", "topics"}


def is_article_url(url: str) -> bool:
    path = urlparse(url).path.rstrip("/")
    if not path.startswith("/news/"):
        return False
    if path.startswith("/news/live/"):
        return False
    if path.startswith("/news/topics/"):
        return False

    slug = path.split("/")[-1]
    if not slug:
        return False
    if path.startswith("/news/articles/"):
        return True
    return any(character.isdigit() for character in slug)


def normalize_url(href: str) -> str:
    return urljoin(BBC_ROOT, href.split("?")[0])


def article_id_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1] or path.replace("/", "_")


def category_slug_from_url(url: str) -> str | None:
    path = urlparse(url).path.rstrip("/")
    parts = [part for part in path.split("/") if part]
    if len(parts) != 2 or parts[0] != "news":
        return None
    slug = parts[1]
    if slug in _CATEGORY_EXCLUDE:
        return None
    if not slug.replace("_", "").replace("-", "").isalpha():
        return None
    return slug


def label_from_slug(slug: str) -> str:
    return slug.replace("_", " ").replace("-", " ").title()
