# -*- coding: utf-8 -*-
"""Constants for license-controlled features."""

DEFAULT_FEATURES = [
    "检测任务",
    "分割任务",
    "EL隐裂",
    "红外",
    "可见光",
]

# Mapping between Chinese license features and their English equivalents
FEATURE_MAPPING = {
    # 任务类型映射（中文主键）
    "检测任务": ["检测任务", "Detection Task"],
    "分割任务": ["分割任务", "Segmentation Task"],
    
    # 图像类型映射（中文主键）
    "红外": ["红外", "Thermal"],
    "可见光": ["可见光", "Visible"],
    "EL隐裂": ["EL隐裂", "EL"],

    # 添加英文主键映射，指向相同的值列表
    "Detection Task": ["检测任务", "Detection Task"],
    "Segmentation Task": ["分割任务", "Segmentation Task"],
    "Thermal": ["红外", "Thermal"],
    "Visible": ["可见光", "Visible"],
    "EL": ["EL隐裂", "EL"],
}

def is_feature_enabled(feature_name: str, enabled_features: list) -> bool:
    """
    Check if a feature is enabled by matching against all possible names.
    
    Args:
        feature_name: The feature name to check (can be in any language)
        enabled_features: List of enabled features from license
        
    Returns:
        bool: True if the feature is enabled
    """
    # Direct match
    if feature_name in enabled_features:
        return True
    
    # Check through mapping
    for license_feature, all_names in FEATURE_MAPPING.items():
        if feature_name in all_names and license_feature in enabled_features:
            return True
    
    return False

def get_enabled_task_types(available_task_types: list, enabled_features: list) -> list:
    """
    Get the list of task types that are enabled by the license.
    
    Args:
        available_task_types: List of task types from UI (language-dependent)
        enabled_features: List of enabled features from license
        
    Returns:
        list: Filtered list of enabled task types
    """
    enabled_types = []
    for task_type in available_task_types:
        if is_feature_enabled(task_type, enabled_features):
            enabled_types.append(task_type)
    
    return enabled_types
