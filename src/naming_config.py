import json
import os
from typing import Any, Dict
import streamlit as st

try:
    from streamlit_change_language import ChangeLanguage
except Exception:  # pragma: no cover - fallback when package is missing

    class ChangeLanguage:
        def __init__(self, languages, default_language="zh"):
            self.languages = languages
            self.default_language = default_language

        def render(self) -> str:
            return st.sidebar.selectbox("Language", self.languages, index=0)


available_languages = ["zh", "en"]
LOCALE_DIR = os.path.join(os.path.dirname(__file__), "locales")
_current_language = st.session_state.get("language", "zh")
_language_changer = ChangeLanguage(
    available_languages, default_language=_current_language
)


def _load_translations(lang: str) -> Dict[str, Any]:
    path = os.path.join(LOCALE_DIR, f"{lang}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


_translations: Dict[str, Any] = _load_translations(_current_language)


# Update globals from translations for backward compatibility


def _update_globals() -> None:
    for key, value in _translations.items():
        globals()[key] = value


_update_globals()

# Load English mappings for language-independent comparisons
_en_translations: Dict[str, Any] = _load_translations("en")
_EN_IMAGE_TYPE_MAP = _en_translations.get("IMAGE_TYPE_MAP", {})
_EN_TASK_TYPE_MAP = _en_translations.get("TASK_TYPE_MAP", {})


def normalize_image_type(name: str) -> str:
    """Return a language-neutral image type."""
    return _EN_IMAGE_TYPE_MAP.get(name, name)


def normalize_task_type(name: str) -> str:
    """Return a language-neutral task type."""
    return _EN_TASK_TYPE_MAP.get(name, name)


def set_language(lang: str) -> None:
    """Set current language and reload translations."""
    global _current_language, _translations
    if lang not in available_languages:
        return
    _current_language = lang
    st.session_state["language"] = lang
    _translations = _load_translations(lang)
    _update_globals()


def get_current_language() -> str:
    return _current_language


# Wrapper helpers -------------------------------------------------------------


def _get(category: str, key: str) -> str:
    return globals().get(category, {}).get(key, key)


def get_sidebar_header(key: str) -> str:
    return _get("SIDEBAR_HEADERS", key)


def get_sidebar_label(key: str) -> str:
    return _get("SIDEBAR_LABELS", key)


def get_sidebar_option(key: str):
    return globals().get("SIDEBAR_OPTIONS", {}).get(key, [])


def get_sidebar_hint(hint_key: str, **kwargs) -> str:
    template = globals().get("SIDEBAR_HINTS", {}).get(hint_key, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_main_header(key: str) -> str:
    return _get("MAIN_HEADERS", key)


def get_main_label(key: str) -> str:
    return _get("MAIN_LABELS", key)


def get_main_option(key: str):
    return globals().get("MAIN_OPTIONS", {}).get(key, [])


def get_button_text(key: str) -> str:
    return _get("BUTTON_TEXTS", key)


def get_image_display_label(key: str) -> str:
    return _get("IMAGE_DISPLAY_LABELS", key)


def get_statistic_label(key: str, **kwargs) -> str:
    template = globals().get("STATISTICS_LABELS", {}).get(key, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_detection_message(message_type: str, **kwargs) -> str:
    template = globals().get("DETECTION_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_file_message(message_type: str, **kwargs) -> str:
    template = globals().get("FILE_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_video_message(message_type: str, **kwargs) -> str:
    template = globals().get("VIDEO_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_camera_message(message_type: str, **kwargs) -> str:
    template = globals().get("CAMERA_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_rtsp_message(message_type: str, **kwargs) -> str:
    template = globals().get("RTSP_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_model_message(message_type: str, **kwargs) -> str:
    template = globals().get("MODEL_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_warning_message(message_type: str, **kwargs) -> str:
    template = globals().get("WARNING_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_general_message(message_type: str, **kwargs) -> str:
    template = globals().get("GENERAL_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_export_message(message_type: str, **kwargs) -> str:
    template = globals().get("EXPORT_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_statistic_message(message_type: str, **kwargs) -> str:
    template = globals().get("STATISTICS_LABELS", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_metric_label(key: str) -> str:
    return _get("METRICS_LABELS", key)


def generate_filename(template_type: str, **kwargs) -> str:
    template = globals().get("FILENAME_TEMPLATES", {}).get(template_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_status_message(message_type: str, **kwargs) -> str:
    template = globals().get("STATUS_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
