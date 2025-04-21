# -*- coding: utf-8 -*-

# Define the Chinese names for each class
Chinese_name = {
    'crack': "裂纹",
    'defect': "缺陷",
    'hotspot': "热点",
    'broken_cell': "破损电池片",
    'discoloration': "变色",
    'thermal_anomaly': "热异常",
    'overheating': "过热",
    'coldspot': "冷点",
    'solar_panel': "太阳能板"
}

# Define a color for each class (in BGR format for OpenCV)
Class_colors = {
    'crack': (0, 0, 255),             # Red
    'defect': (0, 255, 255),          # Yellow
    'hotspot': (0, 165, 255),         # Orange
    'broken_cell': (255, 0, 0),       # Blue
    'discoloration': (255, 255, 0),   # Cyan
    'thermal_anomaly': (128, 0, 128), # Purple
    'overheating': (0, 128, 255),     # Light Orange
    'coldspot': (255, 255, 255),      # White
    'solar_panel': (0, 255, 0)        # Green for solar panels
}

Label_list = list(Chinese_name.values())
