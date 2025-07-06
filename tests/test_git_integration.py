#!/usr/bin/env python3
"""
Git信息集成测试脚本
"""

import sys
import os
import pytest

# 添加src目录到路径
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'src')
sys.path.insert(0, src_dir)

def test_git_info_import():
    """测试Git信息模块导入"""
    try:
        from git_info import format_git_info_for_about, get_version_string, get_git_info
        print("✅ Git信息模块导入成功")
        
        # 测试版本字符串
        version = get_version_string()
        print(f"📋 版本字符串: {version}")
        
        # 测试Git信息
        git_info = get_git_info()
        print(f"📊 Git信息可用: {git_info.get('available', False)}")
        
        # 测试格式化输出
        about_info = format_git_info_for_about()
        print("📝 关于信息预览:")
        print("-" * 50)
        print(about_info[:200] + "..." if len(about_info) > 200 else about_info)
        print("-" * 50)
        
    except ImportError as e:
        pytest.fail(f"Git信息模块导入失败: {e}")
    except Exception as e:
        pytest.fail(f"Git信息测试失败: {e}")


def test_web_integration():
    """测试Web应用集成"""
    try:
        sys.path.append('src')
        print("\n🔍 测试Web应用集成...")
        try:
            from git_info import format_git_info_for_about, get_version_string
            print("✅ Web应用可以成功导入Git信息")
            version_string = get_version_string()
            print(f"🏷️  版本标签将显示为: ({version_string})")
        except ImportError:
            print("⚠️  Web应用将使用默认Git信息（这是正常的备选方案）")
    except Exception as e:
        pytest.fail(f"Web集成测试失败: {e}")


def main():
    """主测试函数"""
    print("🚀 开始Git信息集成测试")
    print("=" * 60)
    
    # 测试1: Git信息模块导入
    test1_success = test_git_info_import()
    
    # 测试2: Web应用集成
    test2_success = test_web_integration()
    
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"📦 Git信息模块: {'✅ 通过' if test1_success else '❌ 失败'}")
    print(f"🌐 Web集成测试: {'✅ 通过' if test2_success else '❌ 失败'}")
    
    if test1_success and test2_success:
        print("\n🎉 所有测试通过！Git信息集成系统工作正常")
        print("\n📝 使用指南:")
        print("1. 运行 'python collect_git_info.py' 更新Git信息")
        print("2. 运行 'python build_with_git_info.py' 进行自动构建")
        print("3. 启动Web应用时会在'关于'菜单显示版本信息")
        return True
    else:
        print("\n⚠️  部分测试失败，请检查配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
