import sys
import os
import argparse
import streamlit.web.cli as stcli
import random
import tempfile
import time
import os
import cv2
import json
import numpy as np
import streamlit as st
from QtFusion.path import abs_path
from QtFusion.utils import drawRectBox
from log import ResultLogger, LogTable
from model import Web_Detector
from chinese_name_list import EL_type, EL_class_colors, Thermo_type, Other_type, Thermo_class_colors, Visible_type, Visible_class_colors, Segmentation_type, Segmentation_class_colors, Other_class_colors
from ui_style import def_css_html
from utils import is_black_and_white, save_uploaded_file, concat_results, load_default_image, get_camera_names, draw_detections, save_chinese_image, format_time, convert_to_pseudo_colorizer, camera_undistortion, auto_undistort_image, rotate_image
import tempfile
from datetime import datetime
from auth import verify_token, get_access_token
import IMcore
import efficientnet_pytorch
from check_license import check_license
from QtFusion.path import abs_path
import numpy
import IMcore
import cryptography
import _cffi_backend


# 设置环境变量以避免 OpenMP 错误
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ENABLE_OAUTH"] = "FALSE"

def run_streamlit(script_path):
    """
    使用 streamlit.web.cli 模块运行 Streamlit 脚本。
    Args:
        script_path (str): 要运行的脚本路径
    Returns:
        None
    """
    # 保存原始命令行参数
    original_argv = sys.argv.copy()
    
    try:
        # 设置 streamlit 运行参数
        sys.argv = [
            "streamlit",
            "run",
            script_path,
            "--global.developmentMode=false",
        ]
        # 执行 streamlit CLI
        stcli.main()
    except Exception as e:
        print(f"Streamlit 脚本运行出错: {e}")
    finally:
        # 恢复原始命令行参数
        sys.argv = original_argv

if __name__ == "__main__":
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser(description="Run the application in different modes.")
    parser.add_argument("--secret-key", required=True, help="Secret key for license encryption/decryption.")
    parser.add_argument("--license-file", default="license.dat", help="Path to the license file.")
    parser.add_argument("--bind-info-file", default="bind_info.json", help="Path to the bind info file.")
    parser.add_argument("--run-mode", default="api", choices=["streamlit", "api"], help="Mode to run the application (streamlit or api).")
    parser.add_argument("--oauth2-introspect-url", default="https://your-auth-server.com/oauth2/introspect", help="OAuth2 introspection URL.")
    parser.add_argument("--oauth2-token-url", default="https://your-auth-server.com/oauth2/token", help="OAuth2 token endpoint URL.")
    parser.add_argument("--client-id", default="your-client-id", help="OAuth2 client ID.")
    parser.add_argument("--client-secret", default="your-client-secret", help="OAuth2 client secret.")
    args = parser.parse_args()

    # 将 SECRET_KEY 转换为字节
    secret_key = args.secret_key.encode()
    check_license(secret_key, args.license_file, args.bind_info_file)

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
        socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    else:
        print(f"Invalid RUN_MODE: {args.run_mode}. Please use 'streamlit' or 'api'.")
