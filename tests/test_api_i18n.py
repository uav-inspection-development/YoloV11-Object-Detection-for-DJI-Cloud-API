#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 国际化功能测试脚本
测试 api_server.py 中的国际化支持功能
"""

import requests
import json
import sys
import os

# 添加 src 目录到路径，以便导入模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

API_BASE_URL = "http://localhost:5000/api"

def test_language_switching():
    """测试语言切换功能"""
    print("🌐 测试API语言切换功能")
    print("=" * 50)
    
    # 测试设置为英文
    print("\n1. 设置语言为英文")
    response = requests.post(f"{API_BASE_URL}/language", 
                           json={"language": "en"},
                           headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功设置语言: {result}")
    else:
        print(f"❌ 设置语言失败: {response.status_code}, {response.text}")
    
    # 获取类型信息（英文）
    print("\n2. 获取类型信息（英文）")
    response = requests.get(f"{API_BASE_URL}/types",
                          headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        types_en = response.json()
        print("✅ 英文类型信息:")
        for task_type, image_types in types_en.items():
            print(f"  📋 {task_type}:")
            for img_type in image_types.keys():
                print(f"    🖼️  {img_type}")
    else:
        print(f"❌ 获取类型信息失败: {response.status_code}")
    
    # 测试设置为中文
    print("\n3. 设置语言为中文")
    response = requests.post(f"{API_BASE_URL}/language",
                           json={"language": "zh"},
                           headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        result = response.json()
        print(f"✅ 成功设置语言: {result}")
    else:
        print(f"❌ 设置语言失败: {response.status_code}, {response.text}")
    
    # 获取类型信息（中文）
    print("\n4. 获取类型信息（中文）")
    response = requests.get(f"{API_BASE_URL}/types",
                          headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        types_zh = response.json()
        print("✅ 中文类型信息:")
        for task_type, image_types in types_zh.items():
            print(f"  📋 {task_type}:")
            for img_type in image_types.keys():
                print(f"    🖼️  {img_type}")
    else:
        print(f"❌ 获取类型信息失败: {response.status_code}")


def test_header_language_detection():
    """测试请求头语言检测"""
    print("\n\n🔍 测试请求头语言检测功能")
    print("=" * 50)
    
    # 测试英文请求头
    print("\n1. 使用英文Accept-Language请求头")
    response = requests.get(f"{API_BASE_URL}/types",
                          headers={
                              "Authorization": "Bearer test_token",
                              "Accept-Language": "en-US,en;q=0.9"
                          })
    if response.status_code == 200:
        types = response.json()
        task_keys = list(types.keys())
        print(f"✅ 检测到英文，任务类型: {task_keys}")
    else:
        print(f"❌ 请求失败: {response.status_code}")
    
    # 测试中文请求头
    print("\n2. 使用中文Accept-Language请求头")
    response = requests.get(f"{API_BASE_URL}/types",
                          headers={
                              "Authorization": "Bearer test_token",
                              "Accept-Language": "zh-CN,zh;q=0.9"
                          })
    if response.status_code == 200:
        types = response.json()
        task_keys = list(types.keys())
        print(f"✅ 检测到中文，任务类型: {task_keys}")
    else:
        print(f"❌ 请求失败: {response.status_code}")
    
    # 测试自定义语言请求头
    print("\n3. 使用自定义X-Language请求头")
    response = requests.get(f"{API_BASE_URL}/types",
                          headers={
                              "Authorization": "Bearer test_token",
                              "X-Language": "en"
                          })
    if response.status_code == 200:
        types = response.json()
        task_keys = list(types.keys())
        print(f"✅ 使用自定义请求头，任务类型: {task_keys}")
    else:
        print(f"❌ 请求失败: {response.status_code}")


def test_query_parameter_language():
    """测试查询参数语言设置"""
    print("\n\n🔗 测试查询参数语言设置")
    print("=" * 50)
    
    # 测试英文查询参数
    print("\n1. 使用lang=en查询参数")
    response = requests.get(f"{API_BASE_URL}/types?lang=en",
                          headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        types = response.json()
        task_keys = list(types.keys())
        print(f"✅ 使用查询参数lang=en，任务类型: {task_keys}")
    else:
        print(f"❌ 请求失败: {response.status_code}")
    
    # 测试中文查询参数
    print("\n2. 使用lang=zh查询参数")
    response = requests.get(f"{API_BASE_URL}/types?lang=zh",
                          headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        types = response.json()
        task_keys = list(types.keys())
        print(f"✅ 使用查询参数lang=zh，任务类型: {task_keys}")
    else:
        print(f"❌ 请求失败: {response.status_code}")


def test_current_language():
    """测试获取当前语言"""
    print("\n\n📋 测试获取当前语言")
    print("=" * 50)
    
    response = requests.get(f"{API_BASE_URL}/language",
                          headers={"Authorization": "Bearer test_token"})
    if response.status_code == 200:
        lang_info = response.json()
        print(f"✅ 当前语言信息: {lang_info}")
    else:
        print(f"❌ 获取语言信息失败: {response.status_code}")


def validate_parameter_localization():
    """验证参数验证的本地化"""
    print("\n\n🛡️ 测试参数验证本地化")
    print("=" * 50)
    
    # 测试无效的model_type（应该根据当前语言返回相应的错误信息）
    print("\n1. 测试无效的model_type参数")
    
    # 先设置为英文
    requests.post(f"{API_BASE_URL}/language", 
                 json={"language": "en"},
                 headers={"Authorization": "Bearer test_token"})
    
    # 测试无效参数
    files = {'image': ('test.jpg', b'fake_image_data', 'image/jpeg')}
    data = {
        'conf_threshold': '0.5',
        'iou_threshold': '0.4', 
        'model_type': 'Invalid Task',  # 无效的任务类型
        'image_type': 'Visible',
        'selected_classes': '["class1"]',
        'enable_pseudo_color': 'false',
        'undistortion_method': 'None'
    }
    
    response = requests.post(f"{API_BASE_URL}/detect/image",
                           files=files,
                           data=data,
                           headers={"Authorization": "Bearer test_token"})
    
    if response.status_code == 400:
        error_info = response.json()
        print(f"✅ 英文错误信息: {error_info}")
    else:
        print(f"❌ 预期400错误，实际: {response.status_code}")
    
    # 再设置为中文测试
    requests.post(f"{API_BASE_URL}/language",
                 json={"language": "zh"},
                 headers={"Authorization": "Bearer test_token"})
    
    data['model_type'] = '无效任务'  # 中文的无效任务类型
    data['image_type'] = '可见光'
    
    response = requests.post(f"{API_BASE_URL}/detect/image",
                           files=files,
                           data=data,
                           headers={"Authorization": "Bearer test_token"})
    
    if response.status_code == 400:
        error_info = response.json()
        print(f"✅ 中文错误信息: {error_info}")
    else:
        print(f"❌ 预期400错误，实际: {response.status_code}")


def main():
    """主测试函数"""
    print("🚀 开始API国际化功能测试")
    print("请确保API服务器正在运行在 http://localhost:5000")
    print("注意：此测试假设OAuth验证已被禁用或使用测试token")
    
    try:
        # 测试基本连接
        response = requests.get(f"{API_BASE_URL}/language", 
                              headers={"Authorization": "Bearer test_token"},
                              timeout=5)
        if response.status_code != 200:
            print(f"❌ 无法连接到API服务器，状态码: {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ 无法连接到API服务器: {e}")
        print("请确保API服务器正在运行")
        return
    
    # 运行所有测试
    test_language_switching()
    test_header_language_detection()
    test_query_parameter_language()
    test_current_language()
    validate_parameter_localization()
    
    print("\n\n🎉 API国际化功能测试完成！")
    print("请查看上述输出以验证所有功能是否正常工作")


if __name__ == "__main__":
    main()
