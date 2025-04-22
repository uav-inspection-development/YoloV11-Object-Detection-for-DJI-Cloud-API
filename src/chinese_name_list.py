# -*- coding: utf-8 -*-

EL_type = {
    'linear_crack': "线状隐裂",          # Linear crack
    'cross_crack': "十字隐裂",           # Cross crack
    'sheet_crack': "片状隐裂",           # Sheet crack
    'missing_corner': "缺角",           # Missing corner
    'fragment': "碎片",                 # Fragment
    'polarity_short_circuit': "极性反短路",  # Polarity short circuit
    'black_heart_cell': "黑心片",       # Black heart cell
    'black_cell': "黑片",               # Black cell
    'black_edge': "黑边",               # Black edge
    'cell_pollution': "电池片污染",      # Cell pollution
    'cell_inherent_issue': "电池片原生问题", # Cell inherent issue
    'process_issue': "工艺问题",         # Process issue
    'mixed_grade': "混档",              # Mixed grade
    'cold_welding': "虚焊",             # Cold welding
    'broken_grid': "断栅",              # Broken grid
    'over_welding': "过焊",             # Over welding
    'scratch': "划伤"                   # Scratch
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
    'ejgd_ycdw': "二极管短路_异常低温"
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

Segmentation_type = {
    'solar_panel': "太阳能板"           # Solar panel
}

EL_class_colors = {
    "linear_crack": (0, 0, 255),             # Red
    "cross_crack": (0, 0, 200),             # Dark Red
    "sheet_crack": (0, 0, 150),             # Deeper Red
    "missing_corner": (0, 255, 255),               # Yellow
    "fragment": (0, 200, 200),               # Light Yellow
    "polarity_short_circuit": (0, 165, 255),          # Orange
    "black_heart_cell": (255, 0, 0),               # Blue
    "black_cell": (200, 0, 0),                 # Dark Blue
    "black_edge": (150, 0, 0),                 # Deeper Blue
    "cell_pollution": (255, 255, 0),          # Cyan
    "cell_inherent_issue": (200, 200, 0),       # Light Cyan
    "process_issue": (128, 0, 128),            # Purple
    "mixed_grade": (0, 128, 255),               # Light Orange
    "cold_welding": (255, 255, 255),             # White
    "broken_grid": (200, 200, 200),             # Light Gray
    "over_welding": (150, 150, 150),             # Dark Gray
    "scratch": (100, 100, 100)              # Deeper Gray
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
    "ejgd_ycdw": (128, 128, 128)         # Gray
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

Segmentation_class_colors = {
    "solar_panel": (0, 255, 0)                # Green for solar panels
}
