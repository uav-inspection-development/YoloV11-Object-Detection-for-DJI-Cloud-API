import sys
import streamlit.web.cli as stcli
import argparse
from QtFusion.path import abs_path
import subprocess
import os
import argparse
import random
import tempfile
import time
import cv2
import json
import numpy as np
import streamlit as st
from QtFusion.utils import drawRectBox
from datetime import datetime
import IMcore
import efficientnet_pytorch
import cryptography
import _cffi_backend

# 添加 src 目录到模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.append(src_dir)

from log import ResultLogger, LogTable
from model import Web_Detector
from chinese_name_list import EL_type, EL_class_colors, Thermo_type, Other_type, Thermo_class_colors, Visible_type, Visible_class_colors, Segmentation_type, Segmentation_class_colors, Other_class_colors
from ui_style import def_css_html
from utils import is_black_and_white, save_uploaded_file, concat_results, load_default_image, get_camera_names, draw_detections, save_chinese_image, format_time, convert_to_pseudo_colorizer, camera_undistortion, auto_undistort_image, rotate_image
from auth import verify_token, get_access_token
from check_license import check_license
from web import Detection_UI


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

    script_path = abs_path("src/ui.py")

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
