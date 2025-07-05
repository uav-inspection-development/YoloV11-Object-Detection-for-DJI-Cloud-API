#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPS解析功能测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import exifread
    EXIFREAD_AVAILABLE = True
except ImportError:
    EXIFREAD_AVAILABLE = False
    print("警告: exifread库未安装，请运行: pip install exifread")

def extract_gps_info_with_exifread(image_path):
    """
    使用exifread库从图片EXIF信息中提取GPS经纬度信息
    
    Args:
        image_path (str): 图片文件路径
        
    Returns:
        dict: 包含GPS信息的字典，包括经度、纬度、高度等
    """
    if not EXIFREAD_AVAILABLE:
        return None
        
    try:
        print(f"正在解析GPS信息: {image_path}")
        
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f)
        
        if not tags:
            print("未找到EXIF数据")
            return None
            
        print(f"找到EXIF数据，共 {len(tags)} 个标签")
        
        # 查找GPS相关标签
        gps_tags = {}
        for tag in tags.keys():
            if tag.startswith('GPS'):
                gps_tags[tag] = tags[tag]
                print(f"GPS标签: {tag} = {tags[tag]}")
        
        if not gps_tags:
            print("EXIF中未找到GPS信息")
            return None
        
        def convert_to_degrees(value):
            """将GPS坐标从度分秒格式转换为十进制度数"""
            try:
                # exifread返回的是特殊格式，需要特别处理
                value_str = str(value)
                print(f"原始坐标值: {value_str}")
                
                # 处理形如 "[25, 29, 189443/5000]" 的格式
                if '[' in value_str and ']' in value_str:
                    # 去掉方括号并分割
                    coords = value_str.strip('[]').split(', ')
                    if len(coords) == 3:
                        # 处理每个部分，可能包含分数
                        degrees = eval(coords[0])  # 度
                        minutes = eval(coords[1])  # 分
                        seconds = eval(coords[2])  # 秒（可能是分数）
                        result = degrees + (minutes / 60.0) + (seconds / 3600.0)
                        print(f"坐标转换: {value} -> {result}")
                        return result
                
                # 处理直接的分数格式
                elif '/' in value_str:
                    result = eval(value_str)
                    print(f"分数转换: {value} -> {result}")
                    return result
                
                # 处理数字格式
                else:
                    result = float(value_str)
                    print(f"数字转换: {value} -> {result}")
                    return result
                    
            except Exception as e:
                print(f"坐标转换错误: {e}")
                # 尝试另一种方法：直接使用exifread的值
                try:
                    if hasattr(value, 'values') and len(value.values) == 3:
                        # exifread的IfdTag对象有values属性
                        degrees = float(value.values[0].num) / float(value.values[0].den)
                        minutes = float(value.values[1].num) / float(value.values[1].den)
                        seconds = float(value.values[2].num) / float(value.values[2].den)
                        result = degrees + (minutes / 60.0) + (seconds / 3600.0)
                        print(f"使用values属性转换: {result}")
                        return result
                except Exception as e2:
                    print(f"使用values属性转换也失败: {e2}")
                return None
        
        result = {}
        
        # 解析纬度
        if 'GPS GPSLatitude' in gps_tags and 'GPS GPSLatitudeRef' in gps_tags:
            lat = convert_to_degrees(gps_tags['GPS GPSLatitude'])
            lat_ref = str(gps_tags['GPS GPSLatitudeRef'])
            if lat is not None:
                if lat_ref == 'S':
                    lat = -lat
                result['latitude'] = lat
                result['latitude_ref'] = lat_ref
                print(f"纬度: {lat} {lat_ref}")
        
        # 解析经度
        if 'GPS GPSLongitude' in gps_tags and 'GPS GPSLongitudeRef' in gps_tags:
            lon = convert_to_degrees(gps_tags['GPS GPSLongitude'])
            lon_ref = str(gps_tags['GPS GPSLongitudeRef'])
            if lon is not None:
                if lon_ref == 'W':
                    lon = -lon
                result['longitude'] = lon
                result['longitude_ref'] = lon_ref
                print(f"经度: {lon} {lon_ref}")
        
        # 解析高度
        if 'GPS GPSAltitude' in gps_tags:
            try:
                alt_value = str(gps_tags['GPS GPSAltitude'])
                if '/' in alt_value:
                    altitude = eval(alt_value)
                else:
                    altitude = float(alt_value)
                result['altitude'] = altitude
                if 'GPS GPSAltitudeRef' in gps_tags:
                    result['altitude_ref'] = int(str(gps_tags['GPS GPSAltitudeRef']))
                print(f"高度: {altitude}m")
            except Exception as e:
                print(f"高度解析错误: {e}")
        
        # 解析时间戳
        if 'GPS GPSTimeStamp' in gps_tags:
            result['gps_timestamp'] = str(gps_tags['GPS GPSTimeStamp'])
            print(f"GPS时间戳: {gps_tags['GPS GPSTimeStamp']}")
        
        # 解析日期
        if 'GPS GPSDateStamp' in gps_tags:
            result['gps_datestamp'] = str(gps_tags['GPS GPSDateStamp'])
            print(f"GPS日期: {gps_tags['GPS GPSDateStamp']}")
        
        print(f"最终结果: {result}")
        return result if result else None
        
    except Exception as e:
        print(f"提取GPS信息时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def format_gps_info(gps_info):
    """
    格式化GPS信息为可读的字符串
    
    Args:
        gps_info (dict): GPS信息字典
        
    Returns:
        str: 格式化后的GPS信息字符串
    """
    if not gps_info:
        return "未找到GPS信息"
    
    parts = []
    
    # 格式化纬度
    if 'latitude' in gps_info:
        lat_str = f"{gps_info['latitude']:.6f}°"
        if 'latitude_ref' in gps_info:
            lat_str += f" {gps_info['latitude_ref']}"
        parts.append(f"纬度: {lat_str}")
    
    # 格式化经度
    if 'longitude' in gps_info:
        lon_str = f"{gps_info['longitude']:.6f}°"
        if 'longitude_ref' in gps_info:
            lon_str += f" {gps_info['longitude_ref']}"
        parts.append(f"经度: {lon_str}")
    
    # 格式化高度
    if 'altitude' in gps_info:
        alt_str = f"{gps_info['altitude']:.1f}m"
        if 'altitude_ref' in gps_info:
            if gps_info['altitude_ref'] == 1:
                alt_str += " (海平面以下)"
            else:
                alt_str += " (海平面以上)"
        parts.append(f"高度: {alt_str}")
    
    # 格式化时间戳
    if 'gps_timestamp' in gps_info and 'gps_datestamp' in gps_info:
        parts.append(f"GPS时间: {gps_info['gps_datestamp']} {gps_info['gps_timestamp']}")
    
    return "\n".join(parts) if parts else "GPS信息不完整"

def test_gps_parsing():
    """测试GPS解析功能"""
    print("=== GPS解析功能测试 (使用exifread) ===")
    
    if not EXIFREAD_AVAILABLE:
        print("无法进行测试，请先安装exifread库")
        return
    
    # 测试示例图片路径（需要替换为实际的DJI图片路径）
    test_image_paths = [
        "../example/Thermo/image/",
    ]
    
    # 同时测试utils.py中的函数
    print("\n=== 测试utils.py中的extract_gps_info函数 ===")
    try:
        from utils import extract_gps_info as utils_extract_gps_info, format_gps_info as utils_format_gps_info
        UTILS_AVAILABLE = True
    except ImportError as e:
        print(f"无法导入utils模块: {e}")
        UTILS_AVAILABLE = False
    
    for img_path in test_image_paths:
        full_path = os.path.join(os.path.dirname(__file__), img_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            print(f"\n正在测试图片: {img_path}")
            gps_info = extract_gps_info_with_exifread(full_path)
            if gps_info:
                print("✅ 找到GPS信息:")
                print(format_gps_info(gps_info))
            else:
                print("❌ 未找到GPS信息")
        elif os.path.exists(full_path) and os.path.isdir(full_path):
            print(f"📁 扫描目录: {img_path}")
            for file in os.listdir(full_path):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.tif')):
                    file_path = os.path.join(full_path, file)
                    print(f"\n  正在测试图片: {file}")
                    
                    # 测试本地函数
                    print("  使用本地函数:")
                    gps_info = extract_gps_info_with_exifread(file_path)
                    if gps_info:
                        print("    ✅ 找到GPS信息:")
                        formatted = format_gps_info(gps_info)
                        for line in formatted.split('\n'):
                            print(f"      {line}")
                    else:
                        print("    ❌ 未找到GPS信息")
                    
                    # 测试utils.py中的函数
                    if UTILS_AVAILABLE:
                        print("  使用utils.py函数:")
                        gps_info_utils = utils_extract_gps_info(file_path)
                        if gps_info_utils:
                            print("    ✅ 找到GPS信息:")
                            formatted_utils = utils_format_gps_info(gps_info_utils)
                            for line in formatted_utils.split('\n'):
                                print(f"      {line}")
                        else:
                            print("    ❌ 未找到GPS信息")
                    
                    break  # 只测试第一个文件
        else:
            print(f"⚠️ 图片文件不存在: {img_path}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_gps_parsing()
