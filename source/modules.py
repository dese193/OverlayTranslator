APP_NAME = "TranslatorOverlay"
APP_VERSION = "2509-public-w2"

DEFAULT_HOTKEY = 'ctrl+m'
DEFAULT_COPY_HOTKEY = 'ctrl+shift+c'
DEFAULT_PHRASE_TIME_LIMIT = 30
DEFAULT_OVERLAY_DISPLAY_TIME = 15
DEFAULT_SOURCE_LANGUAGE = "pl-PL" 

DEFAULT_FONT_SIZE = 18
DEFAULT_TEXT_COLOR = "white"
DEFAULT_BACKGROUND_COLOR = "rgba(0, 0, 0, 150)"
DEFAULT_PADDING = 10
DEFAULT_OVERLAY_MIN_WIDTH = 250
DEFAULT_OVERLAY_MAX_WIDTH = 800
DEFAULT_OVERLAY_MIN_HEIGHT = 50
DEFAULT_OVERLAY_MAX_HEIGHT = 300
DEFAULT_OVERLAY_SHORT_TEXT_MIN_HEIGHT = 50
DEFAULT_OVERLAY_SHORT_TEXT_MAX_HEIGHT = 70

DEFAULT_OVERLAY_POSITION = "top_center"
DEFAULT_TARGET_LANGUAGE = "en"

DEFAULT_RECOGNIZER_ENGINE = "speech_recognition"

DEFAULT_TRANSLATOR_ENGINE = "libretranslate_local"
DEFAULT_LIBRETRANSLATE_URL = "http://localhost:5000/translate"

DEFAULT_INITIAL_SILENCE_TIMEOUT = 4.0
DEFAULT_SILENCE_TIMEOUT = 0.20

OVERLAY_POSITIONS = {
    "top_left": "Top Left",
    "top_center": "Top Center",
    "top_right": "Top Right",
    "bottom_left": "Bottom Left",
    "bottom_center": "Bottom Center",
    "bottom_right": "Bottom Right",
}

TARGET_LANGUAGES = {
    "en": "English",
    "pl": "Polish",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "ru": "Russian",
    "nl": "Dutch",
    "cs": "Czech",
    "pt": "Portuguese",
}

SOURCE_LANGUAGES = {
    "pl-PL": "Polish",
    "en-US": "English (US)",
    "de-DE": "German",
    "es-ES": "Spanish",
    "it-IT": "Italian",
    "ru-RU": "Russian",
    "nl-NL": "Dutch",
    "cs-CZ": "Czech",
    "pt-PT": "Portuguese",
}

TRANSLATOR_ENGINES = {
    "libretranslate_local": "LibreTranslate (Local)"
}

DEFAULT_CONFIG_STRUCT = {
    "hotkey_translate": DEFAULT_HOTKEY,
    "hotkey_copy": DEFAULT_COPY_HOTKEY,
    "overlay_position": DEFAULT_OVERLAY_POSITION,
    "target_language": DEFAULT_TARGET_LANGUAGE,
    "recognizer_engine": DEFAULT_RECOGNIZER_ENGINE,
    "translator_engine": DEFAULT_TRANSLATOR_ENGINE,
    "libretranslate_url": DEFAULT_LIBRETRANSLATE_URL,
    "source_language": DEFAULT_SOURCE_LANGUAGE,

    "font_size": DEFAULT_FONT_SIZE,
    "text_color": DEFAULT_TEXT_COLOR,
    "background_color": DEFAULT_BACKGROUND_COLOR,
    "padding": DEFAULT_PADDING,
    "overlay_min_width": DEFAULT_OVERLAY_MIN_WIDTH,
    "overlay_max_width": DEFAULT_OVERLAY_MAX_WIDTH,
    "overlay_min_height": DEFAULT_OVERLAY_MIN_HEIGHT,
    "overlay_max_height": DEFAULT_OVERLAY_MAX_HEIGHT,
    "overlay_short_text_min_height": DEFAULT_OVERLAY_SHORT_TEXT_MIN_HEIGHT,
    "overlay_short_text_max_height": DEFAULT_OVERLAY_SHORT_TEXT_MAX_HEIGHT,
    "overlay_display_time": DEFAULT_OVERLAY_DISPLAY_TIME,
    "phrase_time_limit": DEFAULT_PHRASE_TIME_LIMIT,
    "initial_silence_timeout": DEFAULT_INITIAL_SILENCE_TIMEOUT,
    "silence_timeout": DEFAULT_SILENCE_TIMEOUT,
}