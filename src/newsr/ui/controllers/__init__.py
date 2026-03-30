from __future__ import annotations

from ..screens import MoreInfoScreen, ArticleQuestionScreen
from ...domain import ArticleRecord


def article_context_source_text(article: ArticleRecord) -> str:
    return article.source_body[:4000]
