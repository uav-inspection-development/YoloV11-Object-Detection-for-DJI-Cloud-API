# -*- coding: utf-8 -*-

EL_type = {
    'crack': "隐裂",                    # crack
    'missing_corner': "缺角",           # Missing corner
    'fragment': "碎片",                 # Fragment
    'scratch': "划伤",                  # Scratch
    'black_cell': "黑片"                # Black cell
}

Thermo_type = {
    'dyrb': "单一热斑",
    'dmjrb': "大面积热斑",
    'dyrb_ycdw': "单一热斑_异常低温",
    'dmjrb_ycdw': "大面积热斑_异常低温",
    'ycdw': "异常低温",
    'dyrb_ejgdl': "单一热斑_二极管短路",
    'ejgdl': "二极管短路",
    'ygfs': "阳光反射",
    'gfb_zc_rcx': "光伏板正常热成像",
    'ejgdl_ycdw': "二极管短路_异常低温"
}

Visible_type = {
    'yyzd': "遮挡",
    'ygfs': "阳光反射",
    'zw': "脏污",
    'yyzd_zw': "遮挡_脏污",
    'ns': "鸟粪",
    'ygfs_yyzd': "阳光反射_遮挡",
    'yyzd_ns': "遮挡_鸟粪",
    'zw_ns': "脏污_鸟粪",
    'gfbzjbx': "光伏板组件变形",
    'gfbqs': "光伏板缺失",
    'mbsl': "面板碎裂"
}

Other_type = {
    'people': "行人",                # Person
    'vehicle': "车辆",              # Vehicle
}

Segmentation_type = {
    'solar_panel': "太阳能板"           # Solar panel
}

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
    "ygfs_yyzd": (0, 255, 255),        # Yellow
    "yyzd_ns": (128, 0, 128),            # Purple
    "zw_ns": (255, 0, 255),            # Magenta
    "gfbzjbx": (0, 0, 255),          # Red
    "gfbqs": (0, 128, 128),           # Teal
    "mbsl": (128, 255, 128)            # Light Green
}

Other_class_colors = {
    "people": (255, 0, 0),               # Blue
    "vehicle": (0, 255, 0)              # Green
}

Segmentation_class_colors = {
    "solar_panel": (0, 255, 0)                # Green for solar panels
}
