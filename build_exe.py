#!/usr/bin/env python3
"""
PyInstaller 构建脚本
自动收集Git信息并打包应用程序
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import argparse


def run_command(command, description=""):
    """
    执行命令并显示结果

    Args:
        command (str): 要执行的命令
        description (str): 命令描述
    """
    print(f"\n{'=' * 50}")
    if description:
        print(f"📋 {description}")
    print(f"🔧 执行命令: {command}")
    print(f"{'=' * 50}")

    try:
        result = subprocess.run(command, shell=True, check=True)
        print(f"✅ {description or '命令'} 执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description or '命令'} 执行失败: {e}")
        return False


def collect_git_info():
    """收集Git信息"""
    print("\n🔍 收集Git仓库信息...")

    # 确保在正确的目录下
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 运行Git信息收集脚本
    success = run_command(
        "python collect_git_info.py --python src/git_info.py",
        "收集Git信息并生成Python文件"
    )

    if success and os.path.exists("src/git_info.py"):
        print("✅ Git信息文件已生成: src/git_info.py")
        return True
    else:
        print("⚠️  Git信息收集失败，将使用默认信息")
        # 创建默认的git_info.py文件
        create_default_git_info()
        return False


def create_default_git_info():
    """创建默认的Git信息文件"""
    from datetime import datetime

    default_content = f'''"""
默认Git信息文件
构建时间: {datetime.now().isoformat()}
"""

# 默认Git仓库信息
GIT_INFO = {{
    "available": False,
    "commit_hash": "未知",
    "commit_hash_short": "未知", 
    "commit_message": "未知",
    "commit_author": "未知",
    "commit_email": "未知",
    "commit_date": "未知",
    "branch": "未知",
    "tag": "未知",
    "total_commits": 0,
    "repository_url": "未知",
    "build_time": "{datetime.now().isoformat()}"
}}

def get_git_info():
    """获取Git信息"""
    return GIT_INFO

def format_git_info_for_about():
    """格式化Git信息用于关于页面显示"""
    return "### 📊 版本信息\\n未找到Git仓库信息，使用默认配置"

def get_version_string():
    """获取简短的版本字符串"""
    return "未知版本"
'''

    os.makedirs("src", exist_ok=True)
    with open("src/git_info.py", "w", encoding="utf-8") as f:
        f.write(default_content)
    print("✅ 已创建默认Git信息文件")


def build_with_pyinstaller(target_script, output_name=None, additional_args=""):
    """
    使用PyInstaller构建应用

    Args:
        target_script (str): 目标脚本文件
        output_name (str): 输出文件名
        additional_args (str): 额外的PyInstaller参数
    """
    if not os.path.exists(target_script):
        print(f"❌ 目标脚本不存在: {target_script}")
        return False

    print(f"\n🔨 开始构建: {target_script}")
    if output_name:
        print(f"📋 输出名称: {output_name}")

    # 构建PyInstaller命令
    cmd_parts = ["pyinstaller"]

    # 添加基本参数 - 移除 --onefile，使用目录模式
    cmd_parts.extend([
        # "--onefile",  # ❌ 移除此参数，改用目录模式
        "--clean",  # 清理临时文件
        "--paths", "src",  # 添加 src 目录到模块搜索路径
    ])

    # 排除不需要的Qt包 - 新增这部分
    qt_excludes = [
        "PySide6",  # 如果主要使用PyQt5，排除PySide6
        "PyQt6",    # 排除PyQt6
        "PySide2",  # 排除PySide2
        # 如果主要使用PySide6，则改为排除PyQt5：
        # "PyQt5",
        # "PyQt6",
        # "PySide2",
    ]

    for exclude_pkg in qt_excludes:
        cmd_parts.extend(["--exclude-module", exclude_pkg])
        print(f"🚫 排除Qt包: {exclude_pkg}")

    # 根据目标脚本和额外参数决定是否显示控制台
    if "--console" in additional_args:
        cmd_parts.append("--console")
        print("🖥️  使用控制台模式")
    elif "--windowed" in additional_args:
        cmd_parts.append("--windowed")
        print("🪟 使用窗口模式")
    else:
        # 默认：main.py 使用控制台，其他使用窗口模式
        if "main.py" in target_script:
            cmd_parts.append("--console")
            print("🖥️  默认使用控制台模式 (main.py)")
        else:
            cmd_parts.append("--windowed")
            print("🪟 默认使用窗口模式")

    # 添加输出名称
    if output_name:
        cmd_parts.extend(["--name", output_name])

    # 添加图标（如果存在）
    icon_paths = ["icon/logo.ico", "icon/icon.ico", "logo.ico", "icon.ico"]
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            cmd_parts.extend(["--icon", icon_path])
            print(f"🎨 使用图标: {icon_path}")
            break

    # 添加数据文件
    data_dirs = [
        ("weights", "weights"),
        ("icon", "icon"),
        ("fonts", "fonts"),
        ("ultralytics", "ultralytics"),
        ("src", "src"),
    ]

    for src_dir, dst_dir in data_dirs:
        if os.path.exists(src_dir):
            cmd_parts.extend(["--add-data", f"{src_dir};{dst_dir}"])
            print(f"📁 添加数据目录: {src_dir} -> {dst_dir}")

    # 添加隐藏导入
    hidden_imports = [
        "streamlit",
        "ultralytics",
        "cv2",
        "numpy",
        "pandas",
        "torch",
        "torchvision",
        "PIL",
        "git_info",
        # 添加 src 目录中的所有自定义模块
        "log",
        "model",
        "chinese_name_list",
        "ui_style",
        "utils",
        "auth",
        "check_license",
        "web",
        "api_server",
        "train_det",
        "train_interface",
        "train_seg",
        "generate_license",
        # 添加其他可能需要的模块
        "QtFusion",
        "QtFusion.path",
        "QtFusion.utils",
        "IMcore",
        "efficientnet_pytorch",
        "cryptography",
        "_cffi_backend",
        "streamlit.web.cli",
        # 添加常见的隐藏依赖
        "pkg_resources.py2_warn",
        "sklearn.utils._cython_blas",
        "sklearn.neighbors.typedefs",
        "sklearn.neighbors.quad_tree",
        "sklearn.tree._utils",
    ]

    for module in hidden_imports:
        cmd_parts.extend(["--hidden-import", module])

    # 添加额外参数
    if additional_args:
        # 过滤掉已经处理的参数
        filtered_args = []
        args_list = additional_args.split()
        i = 0
        while i < len(args_list):
            arg = args_list[i]
            if arg not in ["--console", "--windowed"]:
                filtered_args.append(arg)
            i += 1

        if filtered_args:
            cmd_parts.extend(filtered_args)
            print(f"⚙️  额外参数: {' '.join(filtered_args)}")

    # 添加目标脚本
    cmd_parts.append(target_script)

    # 执行构建
    command = " ".join(cmd_parts)
    success = run_command(command, f"构建 {target_script} -> {output_name or '默认名称'}")

    if success:
        print(f"✅ 构建成功")
        print(f"📂 输出模式: 目录模式 (包含 _internal 文件夹)")
        if output_name:
            print(f"📁 输出位置: dist/{output_name}/")
        else:
            script_name = os.path.splitext(os.path.basename(target_script))[0]
            print(f"📁 输出位置: dist/{script_name}/")

    return success


def clean_build_artifacts():
    """清理构建产生的临时文件"""
    print("\n🧹 清理构建临时文件...")

    dirs_to_clean = ["build", "__pycache__"]
    files_to_clean = ["*.spec"]

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✅ 已删除目录: {dir_name}")
            except Exception as e:
                print(f"⚠️  删除目录失败 {dir_name}: {e}")

    import glob
    for pattern in files_to_clean:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"✅ 已删除文件: {file_path}")
            except Exception as e:
                print(f"⚠️  删除文件失败 {file_path}: {e}")


def main():
    """主函数"""
    print("🚀 开始PyInstaller构建流程")
    print(f"📁 工作目录: {os.getcwd()}")

    # 步骤1: 收集Git信息
    collect_git_info()

    # 步骤2: 构建主程序 (默认目标)
    print("\n📦 开始构建主程序...")
    if os.path.exists("main.py"):
        success = build_with_pyinstaller(
            "main.py",
            "YoloV11-Detection-System",
            "--console"  # 主程序保留控制台
        )
        if not success:
            print("❌ 主程序构建失败")
            return False
    else:
        print("⚠️  main.py 文件不存在，跳过主程序构建")

    # 步骤5: 清理临时文件
    clean_build_artifacts()

    print("\n🎉 构建完成！")
    print("📁 可执行文件位置: dist/")

    # 显示构建的文件
    if os.path.exists("dist"):
        print("\n📋 已生成的文件:")
        for file_name in os.listdir("dist"):
            file_path = os.path.join("dist", file_name)
            if os.path.isfile(file_path):
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                print(f"  📄 {file_name} ({size_mb:.1f} MB)")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLOv11检测系统构建工具")
    parser.add_argument("--target", help="指定要构建的目标文件")
    parser.add_argument("--name", help="指定输出文件名")
    parser.add_argument("--args", help="额外的PyInstaller参数")
    parser.add_argument("--clean-only", action="store_true", help="仅清理临时文件")

    args = parser.parse_args()

    if args.clean_only:
        clean_build_artifacts()
    elif args.target:
        # 构建指定目标
        collect_git_info()
        build_with_pyinstaller(args.target, args.name, args.args or "")
        clean_build_artifacts()
    else:
        # 默认构建流程
        main()
