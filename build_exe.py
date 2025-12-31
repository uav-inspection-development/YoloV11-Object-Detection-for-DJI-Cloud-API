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

# 添加 utils_data 目录到模块搜索路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils_data'))


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
        subprocess.run(command, shell=True, check=True)
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


def encrypt_ui_file():
    """加密 ui.py 文件"""
    print("\n🔐 正在加密 ui.py 文件...")

    ui_file_path = "src/ui.py"
    if not os.path.exists(ui_file_path):
        print("⚠️  ui.py 文件不存在，跳过加密")
        return None

    try:
        # 检查加密依赖是否可用
        try:
            import cryptography
            from cryptography.fernet import Fernet
            print("✅ cryptography 模块可用")
        except ImportError as crypto_error:
            print(f"❌ cryptography 模块不可用: {crypto_error}")
            print(f"⚠️  将使用原始 ui.py 文件: {ui_file_path}")
            return ui_file_path

        # 导入加密工具
        from util_encryption import create_encrypted_script

        # 读取原始 ui.py 文件
        with open(ui_file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        print("📖 已读取 ui.py 源代码")

        # 创建加密后的脚本
        # 自动生成密码，不添加额外混淆以避免影响Streamlit运行
        encrypted_script = create_encrypted_script(
            source_code,
            password=None,  # 自动生成密码
            add_obfuscation=False  # 不添加混淆，保证Streamlit兼容性
        )

        # 创建临时目录存放加密文件
        temp_dir = "temp_encrypted"
        os.makedirs(temp_dir, exist_ok=True)

        # 保存加密后的ui.py
        encrypted_ui_path = os.path.join(temp_dir, "ui.py")
        with open(encrypted_ui_path, 'w', encoding='utf-8') as f:
            f.write(encrypted_script)

        print(f"✅ ui.py 加密完成，保存到: {encrypted_ui_path}")
        return encrypted_ui_path

    except Exception as e:
        print(f"❌ ui.py 加密失败: {e}")
        print(f"⚠️  将使用原始 ui.py 文件: {ui_file_path}")
        return ui_file_path


def build_streamlit_with_spec():
    """使用自定义spec文件构建Streamlit应用"""
    print("🔧 使用自定义spec文件构建Streamlit应用...")

    spec_file = "streamlit_app.spec"
    if not os.path.exists(spec_file):
        print(f"❌ 找不到spec文件: {spec_file}")
        return False

    # 构建命令
    cmd_parts = [
        "pyinstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]

    command = " ".join(cmd_parts)
    success = run_command(command, f"使用spec文件构建: {spec_file}")

    if success:
        print("✅ 使用spec文件构建成功")
        print("📁 输出位置: dist/YoloV11-Detection-System.exe")

    return success


def build_with_pyinstaller(target_script, output_name=None, windowed=False, additional_args=None):
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

    # 🔐 首先加密 ui.py 文件
    encrypted_ui_path = encrypt_ui_file()

    # 构建PyInstaller命令
    cmd_parts = ["pyinstaller"]

    # 添加基本参数 - 移除 --onefile，使用目录模式
    cmd_parts.extend([
        # "--onefile",  # ❌ 移除此参数，改用目录模式
        "--clean",  # 清理临时文件
        "--noconfirm",  # 跳过用户交互过程
        "--paths", "src",  # 添加 src 目录到模块搜索路径
        "--collect-all", "streamlit",  # 收集所有Streamlit相关文件
        "--collect-all", "streamlit_change_language",  # Streamlit多语言组件资源
        "--collect-all", "PySide6",  # 收集所有PySide6相关文件
        "--collect-all", "QtFusion",  # 收集所有QtFusion相关文件
        "--collect-all", "IMcore",  # 收集所有IMcore相关文件（包括PyArmor模块）
        "--collect-all", "pandas",  # 收集所有pandas相关文件（包括DLL）
        "--collect-all", "numpy",   # 收集所有numpy相关文件（包括DLL）
        "--collect-all", "pyarrow",  # 收集所有pyarrow相关文件（包括DLL）
        "--collect-all", "openpyxl",  # 收集Excel处理相关文件
        "--collect-all", "cryptography",  # 收集所有cryptography相关文件（用于加密）
        "--collect-submodules", "pandas",  # 收集pandas子模块
        "--collect-submodules", "numpy",   # 收集numpy子模块
        "--collect-submodules", "pyarrow",  # 收集pyarrow子模块
        "--collect-submodules", "cryptography",  # 收集cryptography子模块
        "--copy-metadata", "streamlit",  # 复制Streamlit元数据
        "--copy-metadata", "streamlit_change_language",  # Streamlit多语言组件元数据
        "--copy-metadata", "altair",  # Streamlit依赖
        "--copy-metadata", "pillow",  # PIL依赖
        "--copy-metadata", "requests",  # 常见依赖
        "--copy-metadata", "numpy",  # numpy元数据
        "--copy-metadata", "pandas",  # pandas元数据
        "--copy-metadata", "pyarrow",  # pyarrow元数据
        "--copy-metadata", "openpyxl",  # Excel处理元数据
        "--copy-metadata", "cryptography",  # cryptography元数据
        "--copy-metadata", "torch",  # torch元数据
        "--copy-metadata", "torchvision",  # torchvision元数据
        "--copy-metadata", "ultralytics",  # ultralytics元数据
        "--copy-metadata", "opencv-python",  # opencv元数据
        "--copy-metadata", "setuptools",  # setuptools元数据
        "--copy-metadata", "packaging",  # packaging元数据
        "--copy-metadata", "PySide6",  # PySide6元数据
        "--copy-metadata", "QtFusion",  # QtFusion元数据
        "--copy-metadata", "PyYAML",  # PyYAML元数据
        "--copy-metadata", "importlib-metadata",  # importlib元数据
        "--copy-metadata", "typing-extensions",  # typing扩展元数据
        "--copy-metadata", "tzdata",  # 时区数据
    ])

    # 排除不需要的Qt包 - 根据项目实际需求调整
    qt_excludes = [
        # "PySide6",  # ❌ 不要排除PySide6，QtFusion依赖它
        "PyQt6",    # 排除PyQt6
        "PyQt5",    # 排除PyQt5
        "PySide2",  # 排除PySide2
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
        (".streamlit", ".streamlit"),
        ("src/locales", "locales"),  # ✅ 仅包含国际化文件
    ]

    for src_dir, dst_dir in data_dirs:
        if os.path.exists(src_dir):
            cmd_parts.extend(["--add-data", f"{src_dir};{dst_dir}"])
            print(f"📁 添加数据目录: {src_dir} -> {dst_dir}")

    # 添加Streamlit运行必需的ui.py文件（使用加密版本）
    if encrypted_ui_path and os.path.exists(encrypted_ui_path):
        cmd_parts.extend(["--add-data", f"{encrypted_ui_path};src"])
        print(f"📄 添加加密的Streamlit UI文件: {encrypted_ui_path} -> src/ui.py")
    elif os.path.exists("src/ui.py"):
        cmd_parts.extend(["--add-data", "src/ui.py;src"])
        print("📄 添加原始Streamlit UI文件: src/ui.py -> src/")
    else:
        print("⚠️  ui.py文件不存在，Streamlit可能无法正常运行")

    # 添加Streamlit静态文件
    try:
        import streamlit
        streamlit_path = os.path.dirname(streamlit.__file__)
        cmd_parts.extend(["--add-data", f"{streamlit_path}/static;streamlit/static"])
        print(f"📁 添加Streamlit静态文件: {streamlit_path}/static")
    except ImportError:
        print("⚠️  无法导入Streamlit，跳过静态文件添加")

    # 添加隐藏导入
    hidden_imports = [
        # Streamlit核心模块
        "streamlit",
        "streamlit_change_language",
        "streamlit.runtime",
        "streamlit.runtime.caching",
        "streamlit.runtime.legacy_caching",
        "streamlit.runtime.state",
        "streamlit.web",
        "streamlit.web.server",
        "streamlit.web.cli",
        "streamlit.components",
        "streamlit.components.v1",
        "streamlit.elements",
        "streamlit.elements.lib",
        "streamlit.elements.utils",
        "streamlit.runtime.scriptrunner",
        "streamlit.runtime.media_file_manager",
        "streamlit.source_util",
        "streamlit.logger",
        "streamlit.config",
        "streamlit.errors",
        "streamlit.hello",
        "streamlit.proto",
        "streamlit.type_util",
        "streamlit.util",
        "streamlit.delta_generator",
        "streamlit.file_util",
        "streamlit.folder_black_list",
        "streamlit.git_util",
        "streamlit.hashing",
        "streamlit.in_memory_file_manager",
        "streamlit.legacy_caching",
        "streamlit.markdown_util",
        "streamlit.net_util",
        "streamlit.report_thread",
        "streamlit.runtime.uploaded_file_manager",
        "streamlit.string_util",
        "streamlit.version",
        "streamlit.watcher",

        # YOLO和深度学习
        "ultralytics",
        "ultralytics.models",
        "ultralytics.utils",
        "ultralytics.engine",
        "ultralytics.nn",
        "ultralytics.data",
        "torch",
        "torchvision",
        "torchvision.transforms",
        "torchvision.models",

        # 图像处理
        "cv2",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageFont",
        "PIL.ImageTk",

        # 数据处理
        "numpy",
        "pandas",
        "pandas.plotting",
        "pandas._libs",
        "pandas._libs.tslib",
        "pandas._libs.tslibs",
        "pandas._libs.tslibs.base",
        "pandas._libs.tslibs.ccalendar",
        "pandas._libs.tslibs.dtypes",
        "pandas._libs.tslibs.field_array",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.offsets",
        "pandas._libs.tslibs.parsing",
        "pandas._libs.tslibs.period",
        "pandas._libs.tslibs.strptime",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",
        "pandas._libs.tslibs.timezones",
        "pandas._libs.tslibs.tzconversion",
        "pandas._libs.tslibs.vectorized",
        "pandas.io.formats.style",
        "pyarrow",
        "pyarrow.lib",
        "pyarrow._compute",
        "pyarrow._csv",
        "pyarrow._dataset",
        "pyarrow._fs",
        "pyarrow._json",
        "pyarrow._parquet",
        "pyarrow.parquet",
        "openpyxl",

        # 可视化
        "altair",
        "altair.vegalite",
        "altair.utils",
        "matplotlib",
        "matplotlib.pyplot",
        "seaborn",
        "plotly",
        "plotly.graph_objects",
        "plotly.express",

        # 网络和HTTP
        "requests",
        "urllib3",
        "charset_normalizer",
        "idna",
        "certifi",

        # 项目自定义模块
        "git_info",
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

        # 其他依赖
        "QtFusion",
        "QtFusion.path",
        "QtFusion.utils",
        "QtFusion.utils.DetVisual",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",

        # IMcore 相关模块（PyArmor 加密）
        "IMcore",
        "IMcore.IMlibs",
        "IMcore.IMlibs.py312",  # Python 3.12 特定模块
        "IMcore.IMvisual",
        "IMcore.__init__",

        "efficientnet_pytorch",
        "cryptography",
        "cryptography.fernet",
        "cryptography.hazmat",
        "cryptography.hazmat.primitives",
        "cryptography.hazmat.primitives.hashes",
        "cryptography.hazmat.primitives.kdf",
        "cryptography.hazmat.primitives.kdf.pbkdf2",
        "_cffi_backend",
        "pkg_resources.py2_warn",
        "sklearn.utils._cython_blas",
        "sklearn.neighbors.typedefs",
        "sklearn.neighbors.quad_tree",
        "sklearn.tree._utils",
        "scipy",
        "sklearn",
        "pytz",
        "tzdata",
        "click",
        "packaging",
        "typing_extensions",
        "importlib_metadata",
        "zipp",
        "pyarrow",
        "streamlit_webrtc",
        "av",
        "yaml",
        "PyYAML",
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
        print("✅ 构建成功")
        print("📂 输出模式: 目录模式 (包含 _internal 文件夹)")
        if output_name:
            print(f"📁 输出位置: dist/{output_name}/")
        else:
            script_name = os.path.splitext(os.path.basename(target_script))[0]
            print(f"📁 输出位置: dist/{script_name}/")

    # 🧹 清理加密临时文件
    if encrypted_ui_path and "temp_encrypted" in encrypted_ui_path:
        temp_dir = os.path.dirname(encrypted_ui_path)
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"🧹 已清理加密临时目录: {temp_dir}")
            except Exception as e:
                print(f"⚠️  清理加密临时目录失败: {e}")

    return success


def clean_build_artifacts():
    """清理构建产生的临时文件"""
    print("\n🧹 清理构建临时文件...")

    dirs_to_clean = ["build", "__pycache__", "temp_encrypted"]
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


def main(output_name):
    """主函数"""
    print("🚀 开始PyInstaller构建流程")
    print(f"📁 工作目录: {os.getcwd()}")

    # 步骤1: 收集Git信息
    collect_git_info()

    # 步骤2: 尝试使用spec文件构建(推荐)
    print("\n📦 尝试使用spec文件构建...")
    if os.path.exists("streamlit_app.spec"):
        success = build_streamlit_with_spec()
        if success:
            print("✅ 使用spec文件构建成功")
        else:
            print("⚠️ spec文件构建失败，回退到传统方法")

            # 步骤3: 传统方法构建主程序
            print("\n📦 使用传统方法构建主程序...")
            if os.path.exists("main.py"):
                success = build_with_pyinstaller(
                    "main.py",
                    output_name,
                    False,
                    "--console"  # 主程序保留控制台
                )
                if not success:
                    print("❌ 主程序构建失败")
                    return False
            else:
                print("⚠️  main.py 文件不存在，跳过主程序构建")
    else:
        print("⚠️ 找不到streamlit_app.spec文件，使用传统方法")

        # 步骤3: 传统方法构建主程序
        print("\n📦 使用传统方法构建主程序...")
        if os.path.exists("main.py"):
            success = build_with_pyinstaller(
                "main.py",
                output_name,
                False,
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
    parser.add_argument("--target", default="main.py", help="指定要构建的目标文件 (默认: main.py)")
    parser.add_argument("--name", default="YoloV11-Detection-System", help="指定输出文件名 (默认: YoloV11-Detection-System)")
    parser.add_argument("--args", help="额外的PyInstaller参数")
    parser.add_argument("--clean-only", action="store_true", help="仅清理临时文件")
    parser.add_argument("--use-spec", action="store_true", help="仅使用spec文件构建")

    args = parser.parse_args()

    if args.clean_only:
        clean_build_artifacts()
    elif args.use_spec:
        # 仅使用spec文件构建
        collect_git_info()
        build_streamlit_with_spec()
        clean_build_artifacts()
    elif args.target != "main.py":
        # 构建指定目标（非默认main.py）
        collect_git_info()
        build_with_pyinstaller(args.target, args.name, False, args.args or "")
        clean_build_artifacts()
    else:
        # 默认构建流程（构建main.py）
        main(args.name)
