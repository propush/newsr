from __future__ import annotations

from ..config.bootstrap import LANGUAGE_BY_LOCALE

# English and native names of languages that TTS engines commonly support, mapped to ISO 639-1 codes.
_LANGUAGE_NAMES: dict[str, str] = {
    "afrikaans": "af", "albanian": "sq", "amharic": "am", "arabic": "ar", "armenian": "hy",
    "azerbaijani": "az", "basque": "eu", "belarusian": "be", "bengali": "bn", "bangla": "bn",
    "bosnian": "bs", "bulgarian": "bg", "burmese": "my", "catalan": "ca", "chinese": "zh",
    "mandarin": "zh", "cantonese": "zh", "croatian": "hr", "czech": "cs", "danish": "da",
    "dutch": "nl", "flemish": "nl", "english": "en", "estonian": "et", "filipino": "fil",
    "tagalog": "fil", "finnish": "fi", "french": "fr", "galician": "gl", "georgian": "ka",
    "german": "de", "greek": "el", "gujarati": "gu", "hebrew": "he", "hindi": "hi",
    "hungarian": "hu", "icelandic": "is", "indonesian": "id", "irish": "ga", "italian": "it",
    "japanese": "ja", "javanese": "jv", "kannada": "kn", "kazakh": "kk", "khmer": "km",
    "korean": "ko", "lao": "lo", "latvian": "lv", "lithuanian": "lt", "luxembourgish": "lb",
    "macedonian": "mk", "malay": "ms", "malayalam": "ml", "maltese": "mt", "marathi": "mr",
    "mongolian": "mn", "nepali": "ne", "norwegian": "nb", "bokmal": "nb", "pashto": "ps",
    "persian": "fa", "farsi": "fa", "polish": "pl", "portuguese": "pt", "punjabi": "pa",
    "romanian": "ro", "russian": "ru", "serbian": "sr", "sinhala": "si", "slovak": "sk",
    "slovenian": "sl", "somali": "so", "spanish": "es", "castilian": "es", "swahili": "sw",
    "swedish": "sv", "tamil": "ta", "telugu": "te", "thai": "th", "turkish": "tr",
    "ukrainian": "uk", "urdu": "ur", "uzbek": "uz", "vietnamese": "vi", "welsh": "cy",
    "zulu": "zu",
    "русский": "ru", "українська": "uk", "беларуская": "be", "български": "bg", "српски": "sr",
    "deutsch": "de", "français": "fr", "español": "es", "italiano": "it", "português": "pt",
    "polski": "pl", "nederlands": "nl", "čeština": "cs", "slovenčina": "sk", "svenska": "sv",
    "dansk": "da", "norsk": "nb", "suomi": "fi", "magyar": "hu", "română": "ro", "türkçe": "tr",
    "ελληνικά": "el", "עברית": "he", "العربية": "ar", "فارسی": "fa", "हिन्दी": "hi",
    "中文": "zh", "日本語": "ja", "한국어": "ko", "ไทย": "th", "tiếng việt": "vi",
}
_LANGUAGE_CODES = {*LANGUAGE_BY_LOCALE, *_LANGUAGE_NAMES.values()}
_CODE_BY_NAME = {**_LANGUAGE_NAMES, **{name.lower(): code for code, name in LANGUAGE_BY_LOCALE.items()}}
_UKRAINIAN_LETTERS = set("іїєґІЇЄҐ")
_SCRIPT_RANGES: tuple[tuple[int, int, str], ...] = (
    (0x0370, 0x03FF, "el"),
    (0x0400, 0x04FF, "cyrillic"),
    (0x0530, 0x058F, "hy"),
    (0x0590, 0x05FF, "he"),
    (0x0600, 0x06FF, "ar"),
    (0x0900, 0x097F, "hi"),
    (0x0980, 0x09FF, "bn"),
    (0x0A00, 0x0A7F, "pa"),
    (0x0A80, 0x0AFF, "gu"),
    (0x0B80, 0x0BFF, "ta"),
    (0x0C00, 0x0C7F, "te"),
    (0x0C80, 0x0CFF, "kn"),
    (0x0D00, 0x0D7F, "ml"),
    (0x0D80, 0x0DFF, "si"),
    (0x0E00, 0x0E7F, "th"),
    (0x0E80, 0x0EFF, "lo"),
    (0x1000, 0x109F, "my"),
    (0x10A0, 0x10FF, "ka"),
    (0x1100, 0x11FF, "ko"),
    (0x1200, 0x137F, "am"),
    (0x1780, 0x17FF, "km"),
    (0x3040, 0x30FF, "ja"),
    (0x4E00, 0x9FFF, "zh"),
    (0xAC00, 0xD7AF, "ko"),
)


def language_code(name: str | None) -> str | None:
    normalized = " ".join((name or "").strip().lower().replace("_", "-").split())
    if not normalized:
        return None
    if normalized in _LANGUAGE_CODES:
        return normalized
    base_code = normalized.split("-", 1)[0]
    if "-" in normalized and base_code in _LANGUAGE_CODES:
        return base_code
    if normalized in _CODE_BY_NAME:
        return _CODE_BY_NAME[normalized]
    for word in normalized.replace("(", " ").replace(")", " ").split():
        if word in _CODE_BY_NAME:
            return _CODE_BY_NAME[word]
    return None


def detect_script_language(text: str, fallback: str | None) -> str | None:
    counts: dict[str, int] = {}
    latin = 0
    for character in text:
        if not character.isalpha():
            continue
        script = _script_of(character)
        if script is None:
            latin += 1
            continue
        counts[script] = counts.get(script, 0) + 1
    if not counts:
        return fallback
    script, count = max(counts.items(), key=lambda entry: entry[1])
    if count < latin:
        return fallback
    if script == "zh" and counts.get("ja"):
        return "ja"
    if script == "cyrillic":
        return "uk" if any(character in _UKRAINIAN_LETTERS for character in text) else "ru"
    return script


def _script_of(character: str) -> str | None:
    codepoint = ord(character)
    for start, end, script in _SCRIPT_RANGES:
        if start <= codepoint <= end:
            return script
    return None
