from __future__ import annotations

from threading import Thread
from typing import TYPE_CHECKING

from ...scheduling import validate_cron_expression
from ..screens import WatchTopicDialogScreen

if TYPE_CHECKING:
    from ..app import NewsReaderApp


class TopicWatchController:
    def __init__(self, app: NewsReaderApp) -> None:
        self._app = app
        self._extract_thread: Thread | None = None

    def start(self) -> None:
        if self._app.provider_home_open:
            self._open_watch_dialog("")
            return
        article = self._app.current_article
        if article is None or self._extract_thread is not None:
            return
        self._app._refresh.set_status_text(self._app.ui.text("watch_topic.status.extracting"), busy=True)
        self._app.refresh_view()
        thread = Thread(
            target=self._extract_topic_for_current_article,
            args=(article.title, article.source_body),
            name="newsr-watch-topic-extract",
            daemon=True,
        )
        self._extract_thread = thread
        thread.start()

    def _extract_topic_for_current_article(self, article_title: str, article_text: str) -> None:
        try:
            topic_name = self._app.llm_client.extract_watch_topic(article_title, article_text).strip()
            if not topic_name:
                raise ValueError("empty topic name")
            self._call_from_thread(self._open_watch_dialog, topic_name)
        except Exception as exc:
            self._call_from_thread(
                self._show_extract_failed,
                self._app.ui.text("watch_topic.status.extract_failed", error=exc),
            )
        finally:
            self._call_from_thread(self._clear_extract_thread)

    def _open_watch_dialog(self, topic_name: str, update_schedule: str | None = None) -> None:
        default_schedule = self._app.config.articles.update_schedule
        screen = WatchTopicDialogScreen(
            self._app.ui,
            title=self._app.ui.text("watch_topic.dialog.title"),
            body=self._app.ui.text(
                "watch_topic.dialog.body",
                default_schedule=default_schedule,
            ),
            topic_name=topic_name,
            update_schedule=update_schedule,
            topic_placeholder=self._app.ui.text("watch_topic.dialog.topic_placeholder"),
            schedule_placeholder=self._app.ui.text(
                "watch_topic.dialog.schedule_placeholder",
                default_schedule=default_schedule,
            ),
            confirm_label=self._app.ui.text("watch_topic.dialog.confirm"),
            cancel_label=self._app.ui.text("watch_topic.dialog.cancel"),
            schedule_validator=self._validate_schedule,
        )
        self._app.push_screen(screen, callback=self._handle_watch_dialog_result)

    def _handle_watch_dialog_result(self, result: tuple[str, str | None] | None) -> None:
        if result is None:
            self._app._refresh.set_status_text(self._app.ui.text("app.status.ready"), busy=False)
            self._app.refresh_view()
            return
        topic_name, update_schedule = result
        try:
            provider = self._app.create_topic_provider(
                display_name=topic_name,
                topic_query=topic_name,
                update_schedule=update_schedule,
                enabled=True,
            )
        except ValueError as exc:
            existing_topic_name = str(exc) or topic_name
            self._app._refresh.set_status_text(
                self._app.ui.text("watch_topic.status.exists", topic=existing_topic_name),
                busy=False,
                hold_seconds=2.0,
            )
            self._app.refresh_view()
            return
        if self._app.provider_home_open:
            self._app._provider_home.refresh_rows()
        self._app._refresh.set_status_text(
            self._app.ui.text("watch_topic.status.created", topic=topic_name),
            busy=False,
        )
        self._app.refresh_view()
        if self._app._refresh.is_busy:
            self._app._refresh.request_due_refresh_check()
            return
        self._app._refresh.start([provider.provider_id], force=True)

    def _validate_schedule(self, raw: str) -> tuple[str | None, str | None]:
        stripped = raw.strip()
        if not stripped:
            return None, None
        try:
            return validate_cron_expression(stripped), None
        except ValueError as exc:
            return None, self._app.ui.text("watch_topic.error.invalid_schedule", error=exc)

    def _show_extract_failed(self, message: str) -> None:
        self._app._refresh.set_status_text(message, busy=False, hold_seconds=2.0)
        self._app.refresh_view()

    def _clear_extract_thread(self) -> None:
        self._extract_thread = None

    def _call_from_thread(self, callback, *args) -> None:  # type: ignore[no-untyped-def]
        if not self._app.is_running:
            return
        try:
            self._app.call_from_thread(callback, *args)
        except RuntimeError:
            return
