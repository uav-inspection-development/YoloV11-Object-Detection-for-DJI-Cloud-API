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
    'hotspot': "热点",                   # Hotspot
    'overheating': "过热",               # Overheating
    'thermal_crack': "热裂纹",           # Thermal crack
    'delamination': "层压脱落",          # Delamination
    'bypass_diode_failure': "旁路二极管失效", # Bypass diode failure
    'shading': "遮挡",                   # Shading
    'thermal_anomaly': "热异常"          # Thermal anomaly
}

Visible_type = {
    'discoloration': "变色",             # Discoloration
    'broken_glass': "玻璃破裂",          # Broken glass
    'corrosion': "腐蚀",                 # Corrosion
    'delamination': "层压脱落",          # Delamination
    'soiling': "污染",                   # Soiling
    'micro_crack': "微裂纹",             # Micro crack
    'frame_damage': "边框损坏",          # Frame damage
    'cell_misalignment': "电池片错位",   # Cell misalignment
    'burn_marks': "烧痕",                # Burn marks
    'foreign_object': "异物"             # Foreign object
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
    "热点": (0, 0, 255),                  # Red
    "过热": (0, 128, 255),                # Orange
    "热裂纹": (0, 255, 255),              # Yellow
    "层压脱落": (255, 0, 0),               # Blue
    "旁路二极管失效": (128, 0, 128),         # Purple
    "遮挡": (0, 255, 0),                  # Green
    "热异常": (255, 255, 0)               # Cyan
}

Visible_class_colors = {
    "变色": (0, 255, 255),                # Yellow
    "玻璃破裂": (0, 0, 255),               # Red
    "腐蚀": (0, 128, 255),                 # Orange
    "层压脱落": (255, 0, 0),               # Blue
    "污染": (128, 128, 128),               # Gray
    "微裂纹": (0, 255, 0),                 # Green
    "边框损坏": (255, 255, 0),             # Cyan
    "电池片错位": (128, 0, 128),            # Purple
    "烧痕": (0, 0, 128),                   # Dark Red
    "异物": (255, 0, 255)                  # Magenta
}

Segmentation_class_colors = {
    "太阳能板": (0, 255, 0)                # Green for solar panels
}
