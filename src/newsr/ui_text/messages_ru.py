from __future__ import annotations

from typing import Final

RU_MESSAGES: Final[dict[str, str]] = {
    "app.binding.previous": "Назад",
    "app.binding.next": "Вперёд",
    "app.binding.up": "Вверх",
    "app.binding.down": "Вниз",
    "app.binding.pgup": "PgUp",
    "app.binding.pgdn": "PgDn",
    "app.binding.back": "Назад",
    "app.binding.classify": "Категории",
    "app.binding.space": "Space",
    "app.binding.mode": "Режим",
    "app.binding.more_info": "Подробнее",
    "app.binding.ask": "Спросить",
    "app.binding.list": "Список",
    "app.binding.sources": "Источники",
    "app.binding.export": "Экспорт",
    "app.binding.open": "Открыть",
    "app.binding.watch_topic": "Тема",
    "app.binding.download": "Обновить",
    "app.binding.brief": "Краткий обзор",
    "app.binding.help": "Справка",
    "app.binding.providers": "Провайдеры",
    "app.binding.quit": "Выход",
    "app.binding.playlist_add": "В плейлист",
    "app.binding.playlist_add_rest": "Остальные в плейлист",
    "app.binding.play_pause": "Пуск/Пауза",
    "app.binding.playlist": "Плейлист",
    "app.binding.playlist_skip": "Следующая в плейлисте",
    "app.binding.playlist_previous": "Предыдущая статья",
    "app.binding.playlist_seek_forward": "Фрагмент вперёд",
    "app.binding.playlist_seek_back": "Фрагмент назад",
    "clipboard.error": "Системный буфер обмена недоступен: {error}. Копирование через терминал также запрошено.",
    "app.empty.header": "Нет статей в кеше",
    "app.empty.body": "Нажмите D, чтобы загрузить статьи.",
    "app.article.position": "Статья № {current} из {total}",
    "app.article.date": "Дата : {date}",
    "app.article.title": "Заголовок: {title}",
    "app.article.mode": "Режим : {mode}",
    "app.article.mode.full": "полный",
    "app.article.mode.summary": "сводка",
    "app.article.mode.original": "оригинал",
    "app.article.url": "URL: {url}",
    "app.status.ready": "готово",
    "app.status.refresh_already_running": "обновление уже запущено",
    "app.status.fetching_target": "загрузка {provider}: {target}",
    "app.status.failed_to_fetch_target": "не удалось загрузить {provider}: {target}: {error}",
    "app.status.extracting_article": "извлечение {article_id}",
    "app.status.classifying_article": "классификация {article_id}, выполнено {done} из {total}",
    "app.status.translating_article": "перевод {article_id}, выполнено {done} из {total}",
    "app.status.summarizing_article": "создание сводки {article_id}, выполнено {done} из {total}",
    "app.status.classifying_current_article": "классификация категорий статьи...",
    "app.status.article_categories_updated": "категории статьи обновлены",
    "app.status.article_categories_update_failed": "не удалось классифицировать категории статьи: {error}",
    "app.status.browser_open_failed": "не удалось открыть браузер: {error}",
    "app.status.browser_opened": "статья открыта в браузере",
    "app.status.browser_not_confirmed": "браузер не подтвердил запрос на открытие",
    "app.status.no_article_to_export": "нет статьи для экспорта",
    "app.status.checking_llm": "проверка доступности llm...",
    "app.status.exiting": "Выход...",
    "app.status.sources_unchanged": "источники не изменились",
    "app.status.sources_saved": "источники сохранены",
    "app.status.sources_saved_next_refresh": "источники сохранены; следующее обновление применит новые настройки провайдеров",
    "app.status.sources_saved_refreshing": "источники сохранены; обновляются включённые провайдеры",
    "confirm_dialog.llm_unresponsive.header": "LLM недоступна",
    "confirm_dialog.llm_unresponsive.body": "LLM не отвечает: {error}. Повторить?",
    "confirm_dialog.button.retry": "Повторить",
    "confirm_dialog.button.cancel": "Отмена",
    "help.body.reader": (
        "Ctrl+C: копировать выделенный текст (включая macOS Terminal)\n"
        "Cmd+C / Ctrl+Shift+C: копировать, если терминал передаёт сочетание\n"
        "Left/Right: предыдущая/следующая статья\n"
        "Up/Down/PgUp/PgDn/B: прокрутка\n"
        "K: классифицировать категории\n"
        "Space: страница вниз или следующая статья\n"
        "S: переключить режим чтения\n"
        "M: подробнее\n"
        "?: спросить о статье\n"
        "L: список статей\n"
        "A: добавить статью в плейлист\n"
        "Shift+A: добавить эту и следующие статьи в плейлист\n"
        "P: пуск/пауза плейлиста\n"
        "Shift+P: показать плейлист\n"
        "] / [: следующая статья плейлиста / текущая сначала, в её начале — предыдущая\n"
        ". / ,: плейлист на фрагмент вперёд / назад\n"
        "Esc: назад к провайдерам\n"
        "C: источники\n"
        "W: следить за темой\n"
        "E: экспорт текущего вида\n"
        "O: открыть статью в браузере\n"
        "D: принудительно обновить текущего провайдера\n"
        "Ctrl+P: палитра команд / выбор темы\n"
        "H: справка\n"
        "Q: выход"
    ),
    "help.body.provider_home": (
        "Ctrl+C: копировать выделенный текст (включая macOS Terminal)\n"
        "Cmd+C / Ctrl+Shift+C: копировать, если терминал передаёт сочетание\n"
        "Up/Down/PgUp/PgDn: перемещение по провайдерам\n"
        "Enter/Space: открыть выбранного провайдера\n"
        "B: краткий обзор\n"
        "C: управление источниками\n"
        "W: создать отслеживаемую тему\n"
        "D: принудительно обновить все провайдеры\n"
        "P: пуск/пауза плейлиста\n"
        "Shift+P: показать плейлист\n"
        "] / [: следующая статья плейлиста / текущая сначала, в её начале — предыдущая\n"
        ". / ,: плейлист на фрагмент вперёд / назад\n"
        "Ctrl+P: палитра команд / выбор темы\n"
        "H: справка\n"
        "Q: выход"
    ),
    "provider_home.empty": "Нет включённых провайдеров. Нажмите C для управления источниками.",
    "provider_home.hint": "Up/Down: выбор   Enter/Space: открыть провайдер   B: обзор   C: источники   W: тема   D: обновить",
    "provider_home.status.empty": "Нет доступных провайдеров.",
    "provider_home.status.selection": "{provider}: непрочитано {unread}, всего {total}",
    "provider_home.table.provider": "Провайдер",
    "provider_home.table.unread": "Непрочитано",
    "provider_home.table.total": "Всего",
    "provider_group.virtual": "Виртуальные",
    "provider_group.providers": "Провайдеры",
    "provider_group.topics": "Темы",
    "source.binding.close": "Закрыть",
    "source.binding.pane": "Панель",
    "source.binding.toggle": "Переключить",
    "source.binding.refresh": "Обновить",
    "source.binding.schedule": "Расписание",
    "source.binding.delete": "Удалить",
    "source.binding.apply": "Применить",
    "source.header": "Управление источниками",
    "source.loading.status": "Загрузка провайдеров и целей...",
    "source.loading.body": "Загрузка источников...",
    "source.hint": "Space: переключить   U: расписание   X: удалить тему   A: применить",
    "source.status.still_loading": "Источники ещё загружаются.",
    "source.status.refreshing_catalog": "Обновление каталога {provider}...",
    "source.status.failed_load": "Не удалось загрузить источники: {error}",
    "source.status.failed_refresh": "Не удалось обновить источники: {error}",
    "source.status.refreshed_catalog": "Каталог {provider} обновлён.",
    "source.status.unable_to_load": "Не удалось загрузить источники.",
    "source.status.counts": "Загружено провайдеров: {providers}. Включено: {enabled}. Всего выбрано целей: {selected}.",
    "source.table.provider": "Провайдер",
    "source.table.type": "Тип",
    "source.table.schedule": "Расписание",
    "source.table.target": "Цель",
    "source.provider_type.all": "all",
    "source.provider_type.http": "http",
    "source.provider_type.topic": "topic",
    "source.schedule.default": "по умолчанию",
    "source.schedule.title": "Расписание обновления: {provider}",
    "source.schedule.body": (
        "Введите cron-выражение из 5 полей. Оставьте поле пустым, чтобы использовать глобальное "
        "расписание по умолчанию: {default_schedule}."
    ),
    "source.schedule.placeholder": "Оставьте пустым для {default_schedule}",
    "source.schedule.confirm": "Сохранить",
    "source.schedule.cancel": "Отмена",
    "source.schedule.saved": "Расписание обновления сохранено для {provider}.",
    "source.delete.title": "Удалить отслеживаемую тему",
    "source.delete.body": "Удалить провайдера отслеживаемой темы '{provider}'?",
    "source.delete.confirm": "Удалить",
    "source.delete.cancel": "Отмена",
    "source.delete.deleted": "Отслеживаемая тема удалена.",
    "watch_topic.dialog.title": "Отслеживание темы",
    "watch_topic.dialog.body": (
        "Задайте имя темы и необязательное cron-расписание для этой отслеживаемой темы. "
        "Оставьте расписание пустым, чтобы использовать {default_schedule}."
    ),
    "watch_topic.dialog.topic_placeholder": "Имя темы",
    "watch_topic.dialog.schedule_placeholder": "Оставьте пустым для {default_schedule}",
    "watch_topic.dialog.confirm": "Создать",
    "watch_topic.dialog.cancel": "Отмена",
    "watch_topic.error.topic_required": "Имя темы обязательно.",
    "watch_topic.error.invalid_schedule": "Некорректное cron-расписание: {error}",
    "watch_topic.status.extracting": "извлечение темы из текущей статьи...",
    "watch_topic.status.extract_failed": "не удалось извлечь тему для отслеживания: {error}",
    "watch_topic.status.exists": "тема уже существует: {topic}",
    "watch_topic.status.created": "создана отслеживаемая тема: {topic}",
    "article_qa.binding.close": "Закрыть",
    "article_qa.binding.next": "Следующий",
    "article_qa.binding.previous": "Предыдущий",
    "article_qa.binding.pgup": "PgUp",
    "article_qa.binding.pgdn": "PgDn",
    "article_qa.label.sources": "Источники",
    "article_qa.placeholder": "Спросите что угодно об этой статье",
    "article_qa.hint": (
        "Enter: спросить/открыть источник   Up/Down: история вопросов   "
        "Tab: поле/источники   Esc: закрыть   PgUp/PgDn: прокрутка ответа"
    ),
    "article_qa.header": "Вопросы по статье\nЗаголовок: {title}\nСостояние: {state}",
    "article_qa.transcript.empty": (
        "# Вопросы по статье\n\n"
        "Спросите что угодно об этой статье на любом языке.\n\n"
        "Ответы используют исходный текст статьи и живые результаты DuckDuckGo.\n\n"
        "После закрытия окна ничего из этого чата не сохраняется."
    ),
    "article_qa.transcript.title": "# Вопросы по статье",
    "article_qa.transcript.question": "## Вопрос {index}\n\n**Вы:** {question}",
    "article_qa.transcript.pending": "_Идёт поиск в интернете и подготовка ответа..._",
    "article_qa.transcript.answer_unavailable": (
        "### Ответ недоступен\n\n"
        "Сейчас на этот вопрос нельзя ответить.\n\n"
        "Ошибка: `{error}`"
    ),
    "article_qa.transcript.answer": "### Ответ\n\n{answer}",
    "article_qa.transcript.no_answer": "_Ответ не получен._",
    "article_qa.transcript.sources_title": "### Источники",
    "article_qa.transcript.sources_empty": "### Источники\n\n_Для этого вопроса не найдено публичных результатов поиска._",
    "more_info.binding.close": "Закрыть",
    "more_info.binding.refresh": "Обновить",
    "more_info.binding.previous": "Назад",
    "more_info.binding.next": "Вперёд",
    "more_info.binding.back": "Назад",
    "more_info.binding.space": "Space",
    "more_info.hint": "Esc: закрыть   Space/B: страница   M: обновить   Left/Right: сменить статью",
    "more_info.header": "Подробнее\nЗаголовок: {title}\nСостояние: {state}",
    "more_info.body.unavailable": "# Дополнительная информация недоступна\n\nНе удалось выполнить дополнительный поиск.\n\nОшибка: `{error}`",
    "more_info.body.no_results": "Для этой статьи пока не найдено дополнительного публичного контекста.",
    "more_info.body.loading": "# Подробнее\n\nСбор дополнительного контекста для:\n\n**{title}**\n\nТекущий шаг: {stage}",
    "brief.binding.close": "Закрыть",
    "brief.binding.generate": "Создать",
    "brief.header": "Краткий обзор",
    "brief.period.label": "Период",
    "brief.period.last_24h": "Последние 24 часа",
    "brief.period.last_week": "Последняя неделя",
    "brief.period.all_unread": "Всё непрочитанное",
    "brief.option.only_unread": "Только непрочитанные статьи",
    "brief.option.include_topics": "Включить отслеживаемые темы",
    "brief.option.mark_read": "Отметить выбранные источники прочитанными",
    "brief.button.generate": "Создать",
    "brief.button.cancel": "Отмена",
    "brief.hint": "Tab/Стрелки: переход   Enter/Space: переключить или нажать   G: создать   Esc: отмена/закрыть",
    "brief.body.ready": "# Обзор\n\nВыберите период и нажмите Создать.",
    "brief.body.starting": "# Обзор\n\nЗапуск создания обзора...",
    "brief.body.generating": "# Обзор\n\nСоздание отчёта...\n\nТекущий шаг: {status}",
    "brief.body.cancelled": "# Обзор\n\nСоздание отменено.",
    "brief.body.failed": "# Обзор недоступен\n\nНе удалось создать обзор.\n\nОшибка: `{error}`",
    "brief.status.refresh_busy": "Краткий обзор недоступен во время обновления.",
    "brief.status.selecting_articles": "выбор статей",
    "brief.status.marking_read": "выбранные источники отмечаются прочитанными",
    "brief.status.compressing_summaries": "сжатие сводок {index} из {total}",
    "brief.status.reducing_notes": "сокращение заметок, проход {pass_number}",
    "brief.status.writing_final": "написание итогового обзора",
    "brief.status.repairing_compressed": (
        "исправление сжатой сводки, пакет {batch_index} из {batch_count}, попытка {attempt} из {attempts}"
    ),
    "brief.status.compressed_fallback": "резервная сжатая сводка для пакета {batch_index} из {batch_count}",
    "brief.status.repairing_final": "исправление итогового обзора, попытка {attempt} из {attempts}",
    "brief.status.final_fallback": "использование резервного итогового обзора",
    "brief_reader.binding.close": "Закрыть",
    "brief_reader.binding.pgup": "PgUp",
    "brief_reader.binding.pgdn": "PgDn",
    "brief_reader.header": "Краткий обзор",
    "brief_reader.hint": "Esc: закрыть   Up/Down: прокрутка   Space/B: страница",
    "brief_reader.hint_with_jump": "Номер + Enter: открыть статью   Esc: закрыть   Up/Down: прокрутка",
    "brief_jump.binding.jump": "Перейти",
    "brief_jump.binding.cancel": "Отмена",
    "brief_jump.header": "Переход к статье",
    "brief_jump.body": "Введите номер статьи от 1 до {max_number}.",
    "brief_jump.button.jump": "Перейти",
    "brief_jump.button.cancel": "Отмена",
    "brief_jump.error.empty": "Введите номер статьи.",
    "brief_jump.error.number": "Используйте только цифры.",
    "brief_jump.error.range": "Выберите номер от 1 до {max_number}.",
    "brief_jump.status.not_found": "статья из обзора больше недоступна",
    "playlist.header": "Плейлист: статей {count}, {state}",
    "playlist.state.playing": "воспроизведение",
    "playlist.state.paused": "пауза",
    "playlist.state.stopped": "остановлен",
    "playlist.empty": "Плейлист пуст. Нажмите A при чтении, чтобы добавить статьи.",
    "playlist.hint": "Up/Down: выбор   Enter: играть сейчас   X/Del: удалить   C: очистить   P/Space: пуск/пауза   ]/[: дальше/назад   ./,: вперёд/назад   Esc: закрыть",
    "playlist.binding.close": "Закрыть",
    "playlist.binding.play_pause": "Пуск/Пауза",
    "playlist.binding.remove": "Удалить",
    "playlist.binding.clear": "Очистить",
    "playlist.clear.title": "Очистить плейлист",
    "playlist.clear.body": "Удалить из плейлиста все статьи ({count})?",
    "playlist.clear.confirm": "Очистить",
    "playlist.clear.cancel": "Отмена",
    "playlist.status.empty": "плейлист пуст",
    "playlist.status.added": "добавлено в плейлист: {added}, в очереди {total}",
    "playlist.status.finished": "плейлист закончился",
    "playlist.status.playing": "▶ {title} · {provider} · в очереди {count}",
    "playlist.status.paused": "‖ {title} · {provider} · в очереди {count}",
    "playlist.status.buffering": "… {title} · {provider} · в очереди {count}",
    "playlist.status.starting": "… запуск плейлиста, в очереди {count}",
    "playlist.status.queued": "■ плейлист: в очереди {count}",
    "playlist.status.error": "⚠ TTS: {error}",
    "playlist.speech.intro": "{provider}. Статья {current} из {total}.",
    "quick_nav.binding.close": "Закрыть",
    "quick_nav.header": "Быстрый переход",
    "quick_nav.empty": "Нет переведённых статей.",
    "quick_nav.hint": "Up/Down: выбор   Enter: открыть статью   Esc: закрыть",
    "quick_nav.selection": "Выбрано {current} из {total}",
    "quick_nav.table.date": "Дата",
    "quick_nav.table.title": "Заголовок",
    "quick_nav.table.provider": "Провайдер",
    "quick_nav.table.category": "Категория",
    "export.binding.save_png": "Сохранить PNG",
    "export.binding.copy_png": "Копировать PNG",
    "export.binding.save_markdown": "Сохранить MD",
    "export.binding.copy_markdown": "Копировать MD",
    "export.binding.cancel": "Отмена",
    "export.header": "Экспорт текущего вида",
    "export.body": (
        "Заголовок: {title}\n"
        "Режим: {mode}\n\n"
        "1: Сохранить PNG   2: Копировать PNG\n"
        "3: Сохранить Markdown   4: Копировать Markdown"
    ),
    "export.button.save_png": "Сохранить PNG",
    "export.button.copy_png": "Копировать PNG",
    "export.button.save_markdown": "Сохранить Markdown",
    "export.button.copy_markdown": "Копировать Markdown",
    "export.button.cancel": "Отмена",
    "open_link.binding.open": "Открыть",
    "open_link.binding.cancel": "Отмена",
    "open_link.header": "Открыть ссылку на источник",
    "open_link.source_link": "Ссылка на источник",
    "open_link.body": "Открыть этот источник в браузере?\n\nЗаголовок: {title}\nURL: {url}",
    "open_link.button.open": "Открыть",
    "open_link.button.cancel": "Отмена",
    "status.loading": "загрузка...",
    "status.cached": "в кеше",
    "status.failed": "ошибка",
    "status.asking_search_query": "запрос поискового запроса у настроенной llm...",
    "status.searching_duckduckgo": "поиск в DuckDuckGo...",
    "status.synthesizing_results": "запрос к настроенной llm для синтеза результатов...",
    "status.asking_web_search_query": "запрос веб-поискового запроса у настроенной llm...",
    "status.asking_llm_to_answer": "запрос к настроенной llm для ответа...",
}
