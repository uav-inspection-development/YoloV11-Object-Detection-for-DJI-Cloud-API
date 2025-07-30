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
_language_changer = ChangeLanguage(available_languages, default_language=_current_language)


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


def set_language(lang: str) -> None:
    """Set current language and reload translations."""
    global _current_language, _translations
    if lang not in available_languages:
        return
    _current_language = lang
    st.session_state["language"] = lang
    _translations = _load_translations(lang)
    _update_globals()

    # 更新类别名称 - 使用动态导入避免循环导入
    try:
        import chinese_name_list
        chinese_name_list.update_class_names()
    except (ImportError, AttributeError):
        pass  # 如果导入失败，忽略


def get_current_language() -> str:
    """Get current language."""
    return _current_language


# Wrapper helpers -------------------------------------------------------------

def _get(category: str, key: str, default=None) -> Any:
    """Get value from a category with fallback to default."""
    category_data = globals().get(category, {})
    if isinstance(category_data, dict):
        return category_data.get(key, default if default is not None else key)
    return default if default is not None else key


def get_system_info(key: str) -> str:
    """Get system information value for a given key."""
    return _get("SYSTEM_INFO", key)


def get_sidebar_header(key: str) -> str:
    return _get("SIDEBAR_HEADERS", key)


def get_system_default(key: str) -> Any:
    """Get system default value for a given key."""
    return _get("SYSTEM_DEFAULTS", key, None)


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


def get_image_display_label(message_type: str, **kwargs) -> str:
    template = globals().get("IMAGE_DISPLAY_LABELS", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_about_content(key: str) -> str:
    return _get("ABOUT_SECTION", key)


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


def get_system_message(message_type: str, **kwargs) -> str:
    """Get system message for a given type."""
    template = globals().get("SYSTEM_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_gps_message(message_type: str, **kwargs) -> str:
    """Get GPS message for a given type."""
    template = globals().get("GPS_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_ui_message(message_type: str, **kwargs) -> str:
    """Get UI message for a given type."""
    template = globals().get("UI_MESSAGES", {}).get(message_type, "")
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_table_column(key: str, **kwargs) -> str:
    """Get table column header for a given key."""
    template = _get("TABLE_COLUMNS", key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_class_names(category_type: str = None):
    """Get class names from translations.

    Args:
        category_type (str, optional): Specific category type to get.
                                      If None, returns all class names.

    Returns:
        dict: Class names dictionary
    """
    class_names = globals().get("CLASS_NAMES", {})
    if category_type:
        return class_names.get(category_type.upper(), {})
    return class_names


def get_report_field(key: str, **kwargs) -> str:
    """Get report field translation for a given key."""
    template = _get("REPORT_FIELDS", key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_fault_category(key: str, **kwargs) -> str:
    """Get fault category translation for a given key."""
    template = _get("FAULT_CATEGORIES", key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_report_statistic(key: str, **kwargs) -> str:
    """Get report statistics translation for a given key."""
    template = _get("REPORT_STATISTICS", key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def get_report_table_header(key: str, **kwargs) -> str:
    """Get report table header translation for a given key."""
    table_headers = globals().get("REPORT_STATISTICS", {}).get("table_headers", {})
    template = table_headers.get(key, key)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
