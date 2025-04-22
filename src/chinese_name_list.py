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
    'dyrb_zd': "单一热斑_遮挡",
    'zd_hw': "遮挡_红外",
    'dmhrb_zd': "大面积热斑_遮挡",
    'ycdw_zd': "异常低温_遮挡",
    'ejgdl': "二极管短路",
    'ygfs_hw': "阳光反射_红外",
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
    "线状隐裂": (0, 0, 255),             # Red
    "十字隐裂": (0, 0, 200),             # Dark Red
    "片状隐裂": (0, 0, 150),             # Deeper Red
    "缺角": (0, 255, 255),               # Yellow
    "碎片": (0, 200, 200),               # Light Yellow
    "极性反短路": (0, 165, 255),          # Orange
    "黑心片": (255, 0, 0),               # Blue
    "黑片": (200, 0, 0),                 # Dark Blue
    "黑边": (150, 0, 0),                 # Deeper Blue
    "电池片污染": (255, 255, 0),          # Cyan
    "电池片原生问题": (200, 200, 0),       # Light Cyan
    "工艺问题": (128, 0, 128),            # Purple
    "混档": (0, 128, 255),               # Light Orange
    "虚焊": (255, 255, 255),             # White
    "断栅": (200, 200, 200),             # Light Gray
    "过焊": (150, 150, 150),             # Dark Gray
    "划伤": (100, 100, 100)              # Deeper Gray
}

Thermo_class_colors = {
    "单一热斑": (0, 0, 255),               # Red
    "大面积热斑": (0, 128, 255),           # Orange
    "单一热斑_异常低温": (0, 255, 255),     # Yellow
    "大面积热斑_异常低温": (255, 0, 0),      # Blue
    "异常低温": (128, 0, 128),             # Purple
    "单一热斑_遮挡": (0, 255, 0),          # Green
    "遮挡_红外": (255, 255, 0),            # Cyan
    "大面积热斑_遮挡": (0, 0, 128),         # Dark Red
    "异常低温_遮挡": (255, 0, 255),         # Magenta
    "二极管短路": (128, 128, 128),         # Gray
    "阳光反射_红外": (0, 128, 128),         # Teal
    "二极管短路_异常低温": (128, 255, 128)  # Light Green
}

Visible_class_colors = {
    "遮挡": (0, 255, 0),                   # Green
    "阳光反射": (255, 255, 0),             # Cyan
    "脏污": (128, 128, 128),               # Gray
    "遮挡_脏污": (0, 128, 255),            # Orange
    "鸟粪": (255, 0, 0),                   # Blue
    "阳光反射_遮挡": (0, 255, 255),        # Yellow
    "遮挡_鸟粪": (128, 0, 128),            # Purple
    "脏污_鸟粪": (255, 0, 255),            # Magenta
    "光伏板组件变形": (0, 0, 255),          # Red
    "光伏板缺失": (0, 128, 128),           # Teal
    "面板碎裂": (128, 255, 128)            # Light Green
}

Segmentation_class_colors = {
    "太阳能板": (0, 255, 0)                # Green for solar panels
}
