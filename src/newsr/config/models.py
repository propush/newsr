from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_UI_CLOCK = "no_seconds"
DEFAULT_TTS_ENGINE = "edge"
TTS_ENGINES = ("openai", "elevenlabs", "edge", "piper", "system", "silero")


@dataclass(slots=True)
class ArticlesConfig:
    fetch: int
    store: int
    timeout: int
    update_schedule: str


@dataclass(slots=True)
class LLMConfig:
    url: str
    model_translation: str
    model_summary: str
    api_key: str | None = None
    headers: dict[str, str] | None = None
    request_retries: int = 2
    brief_context: int = 100000


@dataclass(slots=True)
class TranslationConfig:
    target_language: str


@dataclass(slots=True)
class ProviderSortConfig:
    primary: str
    direction: str


@dataclass(slots=True)
class UIConfig:
    locale: str
    show_all: bool
    provider_sort: ProviderSortConfig
    clock: str = DEFAULT_UI_CLOCK


@dataclass(slots=True)
class ExportImageConfig:
    quality: str


@dataclass(slots=True)
class ExportConfig:
    image: ExportImageConfig


@dataclass(slots=True)
class TTSOpenAIConfig:
    url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini-tts"
    api_key: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    voices: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSElevenLabsConfig:
    url: str = "https://api.elevenlabs.io/v1"
    model: str = "eleven_multilingual_v2"
    api_key: str | None = None
    voices: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSEdgeConfig:
    voices: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSPiperConfig:
    models_dir: str = "cache/piper"
    voices: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSSystemConfig:
    voices: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSSileroConfig:
    models_dir: str = "cache/silero"
    voices: dict[str, str] = field(default_factory=dict)
    lexicon: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TTSConfig:
    engine: str = DEFAULT_TTS_ENGINE
    speed: float = 1.0
    original_language: str = "en"
    request_retries: int = 2
    media_controls: bool = True
    openai: TTSOpenAIConfig = field(default_factory=TTSOpenAIConfig)
    elevenlabs: TTSElevenLabsConfig = field(default_factory=TTSElevenLabsConfig)
    edge: TTSEdgeConfig = field(default_factory=TTSEdgeConfig)
    piper: TTSPiperConfig = field(default_factory=TTSPiperConfig)
    system: TTSSystemConfig = field(default_factory=TTSSystemConfig)
    silero: TTSSileroConfig = field(default_factory=TTSSileroConfig)


@dataclass(slots=True)
class AppConfig:
    articles: ArticlesConfig
    llm: LLMConfig
    translation: TranslationConfig
    ui: UIConfig
    export: ExportConfig
    tts: TTSConfig = field(default_factory=TTSConfig)
