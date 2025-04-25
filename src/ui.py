import sys
import os
import subprocess
import argparse


# 设置环境变量以避免 OpenMP 错误
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ENABLE_OAUTH"] = "FALSE"

from QtFusion.path import abs_path


def run_streamlit(script_path):
    """
    使用当前 Python 环境运行 Streamlit 脚本。

    Args:
        script_path (str): 要运行的脚本路径
        client_id (str): OAuth2 client ID
        client_secret (str): OAuth2 client secret

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
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="Run the application in different modes.")
    parser.add_argument("--run-mode", default="streamlit", choices=["streamlit", "api"], help="Mode to run the application (streamlit or api).")
    parser.add_argument("--oauth2-introspect-url", default="https://your-auth-server.com/oauth2/introspect", help="OAuth2 introspection URL.")
    parser.add_argument("--oauth2-token-url", default="https://your-auth-server.com/oauth2/token", help="OAuth2 token endpoint URL.")
    parser.add_argument("--client-id", default="your-client-id", help="OAuth2 client ID.")
    parser.add_argument("--client-secret", default="your-client-secret", help="OAuth2 client secret.")
    args = parser.parse_args()

    # 设置环境变量以传递 OAuth2 配置
    os.environ["OAUTH2_INTROSPECT_URL"] = args.oauth2_introspect_url
    os.environ["OAUTH2_TOKEN_URL"] = args.oauth2_token_url
    os.environ["CLIENT_ID"] = args.client_id
    os.environ["CLIENT_SECRET"] = args.client_secret

    if args.run_mode == "streamlit":
        # 指定 Streamlit 脚本路径
        script_path = abs_path("web.py")

        # 运行 Streamlit 脚本
        run_streamlit(script_path)

    elif args.run_mode == "api":
        # 运行 Flask API
        from api_server import socketio, app
        socketio.run(app, host="0.0.0.0", port=5000)

    else:
        print(f"Invalid RUN_MODE: {args.run_mode}. Please use 'streamlit' or 'api'.")
