# -*- coding: utf-8 -*-

"""Class name mappings for different languages."""

from typing import Dict

from naming_config import get_current_language


# -----------------------------
# Chinese name dictionaries
# -----------------------------
EL_type_zh = {
    "crack": "隐裂",  # crack
    "missing_corner": "缺角",  # Missing corner
    "fragment": "碎片",  # Fragment
    "scratch": "划伤",  # Scratch
    "black_cell": "黑片",  # Black cell
}

Thermo_type_zh = {
    "dyrb": "单一热斑",
    "dmjrb": "大面积热斑",
    "dyrb_ycdw": "单一热斑_异常低温",
    "dmjrb_ycdw": "大面积热斑_异常低温",
    "ycdw": "异常低温",
    "dyrb_ejgdl": "单一热斑_二极管短路",
    "ejgdl": "二极管短路",
    "ygfs": "阳光反射",
    "gfb_zc_rcx": "光伏板正常热成像",
    "ejgdl_ycdw": "二极管短路_异常低温",
}

Visible_type_zh = {
    "yyzd": "遮挡",
    "ygfs": "阳光反射",
    "zw": "脏污",
    "yyzd_zw": "遮挡_脏污",
    "ns": "鸟粪",
    "yyzd_ns": "遮挡_鸟粪",
    "zw_ns": "脏污_鸟粪",
    "gfbzjbx": "光伏板组件变形",
    "gfbqs": "光伏板缺失",
    "mbsl": "面板碎裂",
    "snow": "积雪",
    "crack": "隐裂",
}

Other_type_zh = {
    "people": "行人",  # Person
    "vehicle": "车辆",  # Vehicle
}

Segmentation_type_zh = {
    "component": "单组件",  # Solar panel
    "string": "组串",  # String of solar panels
}


# -----------------------------
# English name dictionaries
# -----------------------------
EL_type_en = {
    "crack": "crack",
    "missing_corner": "missing corner",
    "fragment": "fragment",
    "scratch": "scratch",
    "black_cell": "black cell",
}

Thermo_type_en = {
    "dyrb": "single hot spot",
    "dmjrb": "large area hot spot",
    "dyrb_ycdw": "single hot spot - low temp",
    "dmjrb_ycdw": "large hot spot - low temp",
    "ycdw": "abnormal low temp",
    "dyrb_ejgdl": "single hot spot - diode short",
    "ejgdl": "diode short",
    "ygfs": "sun reflection",
    "gfb_zc_rcx": "normal thermal imaging",
    "ejgdl_ycdw": "diode short - low temp",
}

Visible_type_en = {
    "yyzd": "obstruction",
    "ygfs": "reflection",
    "zw": "dirt",
    "yyzd_zw": "obstruction_dirt",
    "ns": "bird excrement",
    "yyzd_ns": "obstruction_bird_excrement",
    "zw_ns": "dirt_bird_excrement",
    "gfbzjbx": "module deformation",
    "gfbqs": "module missing",
    "mbsl": "panel cracking",
    "snow": "snow",
    "crack": "crack",
}

Other_type_en = {
    "people": "person",
    "vehicle": "vehicle",
}

Segmentation_type_en = {
    "component": "component",
    "string": "string",
}

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

    if get_current_language() == "en":
        EL_type = EL_type_en
        Thermo_type = Thermo_type_en
        Visible_type = Visible_type_en
        Other_type = Other_type_en
        Segmentation_type = Segmentation_type_en
    else:
        EL_type = EL_type_zh
        Thermo_type = Thermo_type_zh
        Visible_type = Visible_type_zh
        Other_type = Other_type_zh
        Segmentation_type = Segmentation_type_zh


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
    "string": (0, 0, 255)                      # Blue for strings
}
