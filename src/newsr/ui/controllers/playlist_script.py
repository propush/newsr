from __future__ import annotations

from typing import TYPE_CHECKING

from ...domain import ArticleRecord, ReaderState, ViewMode
from ...tts import SpeechSegment, body_language, build_item_script
from .article_rendering import article_text, article_title

if TYPE_CHECKING:
    from ...config.models import AppConfig
    from ...ui_text import UILocalizer


def article_segments(
    ui: UILocalizer,
    config: AppConfig,
    article: ArticleRecord,
    *,
    mode: ViewMode,
    position: int,
    total: int,
    provider_name: str,
    max_chars: int,
) -> tuple[SpeechSegment, ...]:
    reader_state = ReaderState(article_id=article.article_id, view_mode=mode, scroll_offset=0)
    title = article_title(reader_state, article)
    body = article_text(reader_state, article)
    language = body_language(
        mode,
        f"{title}\n{body}",
        target_language=config.translation.target_language,
        original_language=config.tts.original_language,
    )
    return tuple(
        build_item_script(
            intro=ui.text("playlist.speech.intro", provider=provider_name, current=position + 1, total=total),
            intro_language=config.ui.locale,
            title=title,
            body=body,
            body_language=language,
            max_chars=max_chars,
        )
    )


def preparation_texts(
    ui: UILocalizer,
    config: AppConfig,
    article: ArticleRecord,
    *,
    position: int,
    total: int,
    provider_name: str,
    max_chars: int,
) -> list[tuple[str, str | None]]:
    """The `(text, language)` pairs of every reader mode, so a later mode switch needs no new preparation."""
    texts: dict[tuple[str, str | None], None] = {}
    for mode in ViewMode:
        segments = article_segments(
            ui,
            config,
            article,
            mode=mode,
            position=position,
            total=total,
            provider_name=provider_name,
            max_chars=max_chars,
        )
        texts.update(dict.fromkeys((segment.text, segment.language) for segment in segments))
    return list(texts)
