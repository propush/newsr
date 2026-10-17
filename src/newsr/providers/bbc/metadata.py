from __future__ import annotations

import json

from bs4 import BeautifulSoup


def article_metadata(soup: BeautifulSoup) -> dict[str, object]:
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            payload = json.loads(script.string or script.get_text())
        except (ValueError, TypeError):
            continue
        items = payload if isinstance(payload, list) else [payload]
        for item in list(items):
            if isinstance(item, dict) and isinstance(item.get("@graph"), list):
                items.extend(item["@graph"])
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type")
            types = [types] if isinstance(types, str) else types
            if isinstance(types, list) and any(
                value in {"Article", "NewsArticle", "ReportageNewsArticle"}
                for value in types if isinstance(value, str)
            ):
                return item
    return {}


def author_names(metadata: dict[str, object]) -> str | None:
    authors = metadata.get("author")
    authors = authors if isinstance(authors, list) else [authors]
    names: list[str] = []
    for author in authors:
        name = author.get("name") if isinstance(author, dict) else author
        if isinstance(name, str) and name.strip() and name.strip() not in names:
            names.append(name.strip())
    return ", ".join(names) or None
