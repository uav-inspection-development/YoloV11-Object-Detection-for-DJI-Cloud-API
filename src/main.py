import sys
import streamlit.web.cli as stcli
import argparse
from QtFusion.path import abs_path
import subprocess


def run_streamlit(script_path, extra_args=None):
    """
    使用 streamlit.web.cli 模块运行 Streamlit 脚本，并支持传入额外参数。
    Args:
        script_path (str): 要运行的脚本路径
        extra_args (list): 额外的命令行参数
    """
    original_argv = sys.argv.copy()

    try:
        # 基础命令
        sys.argv = [
            "streamlit",
            "run",
            script_path,
            "--global.developmentMode=false",
            "--",
        ]

        # 添加额外参数
        if extra_args:
            sys.argv.extend(extra_args)

        # 调用 Streamlit CLI
        stcli.main()
    except Exception as e:
        print(f"Streamlit 脚本运行出错: {e}")
    finally:
        sys.argv = original_argv


def run_api(script_path, extra_args=None):
    """
    运行 API 脚本，并支持传入额外参数。
    """
    try:
        # 构造命令
        command = ["python", script_path]
        if extra_args:
            command.extend(extra_args)

        # 调用子进程运行 API 脚本
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"API 脚本运行出错: {e}")


if __name__ == "__main__":
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="Run the application in different modes.")
    parser.add_argument("--secret-key", required=True, help="Secret key for license encryption/decryption.")
    parser.add_argument("--license-file", default="license.dat", help="Path to the license file.")
    parser.add_argument("--bind-info-file", default="bind_info.json", help="Path to the bind info file.")
    parser.add_argument("--run-mode", default="streamlit", choices=["streamlit", "api"], help="Mode to run the application (streamlit or api).")
    parser.add_argument("--oauth2-introspect-url", default="https://your-auth-server.com/oauth2/introspect", help="OAuth2 introspection URL.")
    parser.add_argument("--oauth2-token-url", default="https://your-auth-server.com/oauth2/token", help="OAuth2 token endpoint URL.")
    parser.add_argument("--client-id", default="your-client-id", help="OAuth2 client ID.")
    parser.add_argument("--client-secret", default="your-client-secret", help="OAuth2 client secret.")
    
    script_path = abs_path("ui.py")

    if len(sys.argv) == 1:
        run_streamlit(script_path)
    else:
        args = parser.parse_args()
        if args.run_mode == "api":
            # 运行 API 模式
            run_api(script_path, extra_args=sys.argv[1:])
        else:
            # 将 argparse 的参数转换为命令行参数列表
            extra_args = []
            for key, value in vars(args).items():
                if value is not None:  # 忽略 None 值
                    extra_args.append(f"--{key.replace('_', '-')}")
                    extra_args.append(str(value))

            run_streamlit(script_path, extra_args)
