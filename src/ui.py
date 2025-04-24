import sys
import os
import subprocess

# 设置环境变量以避免 OpenMP 错误
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from QtFusion.path import abs_path


# Get the RUN_MODE from the command-line argument
RUN_MODE = sys.argv[1] if len(sys.argv) > 1 else "streamlit"  # Default to "streamlit"

def run_streamlit(script_path):
    """
    使用当前 Python 环境运行 Streamlit 脚本。

    Args:
        script_path (str): 要运行的脚本路径

    Returns:
        None
    """
    # 获取当前 Python 解释器的路径
    python_path = sys.executable

    # 构建运行命令
    command = f'"{python_path}" -m streamlit run "{script_path}"'

    # 执行命令
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print("Streamlit 脚本运行出错。")


if __name__ == "__main__":
    if RUN_MODE == "streamlit":
        # 指定 Streamlit 脚本路径
        script_path = abs_path("web.py")

        # 运行 Streamlit 脚本
        run_streamlit(script_path)

    elif RUN_MODE == "api":
        # 运行 Flask API
        from api_server import socketio, app
        socketio.run(app, host="0.0.0.0", port=5000)

    else:
        print(f"Invalid RUN_MODE: {RUN_MODE}. Please use 'streamlit' or 'api'.")
