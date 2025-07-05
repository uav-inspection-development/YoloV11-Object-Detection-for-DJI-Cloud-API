#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS解析功能测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from utils import extract_gps_info, format_gps_info

def test_gps_parsing():
    """测试GPS解析功能"""
    print("=== GPS解析功能测试 ===")
    
    # 测试示例图片路径（需要替换为实际的DJI图片路径）
    test_image_paths = [
        "example/EL/image/EL_test_001.jpg",
        "example/Thermo/image/",
        "example/Visible/image/",
        "output/image/562408281191243.JPG",
        "output/image/HTD1F3214350837.JPG"
    ]
    
    for img_path in test_image_paths:
        full_path = os.path.join(os.path.dirname(__file__), img_path)
        if os.path.exists(full_path):
            print(f"\n正在测试图片: {img_path}")
            gps_info = extract_gps_info(full_path)
            if gps_info:
                print("✅ 找到GPS信息:")
                print(format_gps_info(gps_info))
            else:
                print("❌ 未找到GPS信息")
        else:
            print(f"⚠️ 图片文件不存在: {img_path}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_gps_parsing()
