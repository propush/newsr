from __future__ import annotations

from .catalog import BASE_TARGET_OPTIONS, TargetOption
from .provider import DEFAULT_TARGET_SLUGS, NineToFiveGoogleProvider
from .parsing import parse_article_html, parse_section_html
from .urls import (
    NINETOFIVEGOOGLE_ROOT,
    article_id_from_url,
    is_article_url,
    normalize_target_path,
    normalize_url,
)

__all__ = [
    "BASE_TARGET_OPTIONS",
    "DEFAULT_TARGET_SLUGS",
    "NineToFiveGoogleProvider",
    "TargetOption",
    "parse_article_html",
    "parse_section_html",
    "NINETOFIVEGOOGLE_ROOT",
    "article_id_from_url",
    "is_article_url",
    "normalize_target_path",
    "normalize_url",
]
