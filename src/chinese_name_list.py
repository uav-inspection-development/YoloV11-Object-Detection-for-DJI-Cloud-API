# -*- coding: utf-8 -*-

"""Class name mappings for different languages."""

from typing import Dict

def get_current_language():
    """获取当前语言，避免循环导入"""
    try:
        import streamlit as st
        return st.session_state.get("language", "zh")
    except:
        return "zh"  # 默认返回中文

def get_class_names():
    """从 locale 文件中获取类别名称"""
    try:
        from naming_config import get_class_names as get_locale_class_names
        return get_locale_class_names()
    except:
        return {}

# -----------------------------
# Globals updated by language
# -----------------------------
EL_type: Dict[str, str] = {}
Thermo_type: Dict[str, str] = {}
Visible_type: Dict[str, str] = {}
Other_type: Dict[str, str] = {}
Segmentation_type: Dict[str, str] = {}


def update_class_names() -> None:
    """Update class name dictionaries based on current language."""
    global EL_type, Thermo_type, Visible_type, Other_type, Segmentation_type

    # 从 locale 文件中获取类别名称
    class_names = get_class_names()
    
    if class_names:
        EL_type = class_names.get("EL", {})
        Thermo_type = class_names.get("Thermal", {})
        Visible_type = class_names.get("Visible", {})
        Other_type = class_names.get("Other", {})
        Segmentation_type = class_names.get("Segmentation", {})
    else:
        print("无法获取类别名称！请检查 locale 文件是否存在或格式是否正确。")


# 添加获取类别名称的便利函数
def get_class_name(category_type: str) -> Dict[str, str]:
    """
    根据类别类型获取对应的类别名称字典
    
    Args:
        category_type (str): 类别类型 ('EL', 'Thermal', 'Visible', 'Other', 'Segmentation')

    Returns:
        Dict[str, str]: 类别名称字典
    """
    category_map = {
        'EL': EL_type,
        'Thermal': Thermo_type,
        'Visible': Visible_type,
        'Other': Other_type,
        'Segmentation': Segmentation_type
    }
    return category_map.get(category_type, {})


# Initialize on import
update_class_names()

EL_class_colors = {
    "crack": (0, 0, 255),                     # Red
    "missing_corner": (0, 255, 255),          # Yellow
    "fragment": (0, 200, 200),                # Light Yellow
    "scratch": (100, 100, 100),               # Deeper Gray
    "black_cell": (200, 0, 0)                 # Dark Blue
}

Thermo_class_colors = {
    "dyrb": (0, 0, 255),               # Red
    "dmjrb": (0, 128, 255),           # Orange
    "dyrb_ycdw": (0, 255, 255),     # Yellow
    "dmjrb_ycdw": (255, 0, 0),      # Blue
    "ycdw": (128, 0, 128),             # Purple
    "dyrb_ejgdl": (0, 255, 0),          # Green
    "ejgdl": (255, 255, 0),            # Cyan
    "ygfs": (0, 0, 128),         # Dark Red
    "gfb_zc_rcx": (255, 0, 255),         # Magenta
    "ejgdl_ycdw": (128, 128, 128)         # Gray
}

Visible_class_colors = {
    "yyzd": (0, 255, 0),                   # Green
    "ygfs": (255, 255, 0),             # Cyan
    "zw": (128, 128, 128),               # Gray
    "yyzd_zw": (0, 128, 255),            # Orange
    "ns": (255, 0, 0),                   # Blue
    "yyzd_ns": (128, 0, 128),            # Purple
    "zw_ns": (255, 0, 255),            # Magenta
    "gfbzjbx": (0, 0, 255),          # Red
    "gfbqs": (0, 128, 128),           # Teal
    "mbsl": (128, 255, 128),            # Light Green
    "snow": (255, 255, 255),            # White
    "crack": (0, 0, 255),                # Red
}

Other_class_colors = {
    "people": (255, 0, 0),               # Blue
    "vehicle": (0, 255, 0)              # Green
}

Segmentation_class_colors = {
    "component": (0, 255, 0),                # Green for single solar panels
    "string": (0, 0, 255),                     # Blue for strings
    "missing_panel": (255, 0, 255)             # Magenta for missing panels
}
