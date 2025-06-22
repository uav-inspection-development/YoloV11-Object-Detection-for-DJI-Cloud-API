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
import numpy
import IMcore
import cryptography
import _cffi_backend
from web import Detection_UI


# 设置环境变量以避免 OpenMP 错误
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ENABLE_OAUTH"] = "FALSE"

def run_streamlit(script_path):
    """
    使用 streamlit.web.cli 模块运行 Streamlit 脚本。
    Args:
        script_path (str): 要运行的脚本路径
    """
    original_argv = sys.argv.copy()

    try:
        sys.argv = [
            "streamlit",
            "run",
            script_path,
            "--global.developmentMode=false",
        ]
        stcli.main()
    except Exception as e:
        print(f"Streamlit 脚本运行出错: {e}")
    finally:
        sys.argv = original_argv

def streamlit_login_page():
    """
    用户登录页：输入参数并保存到 session_state
    """
    st.title("用户登录")
    secret_key = st.text_input("Secret Key", type="password")
    license_file = st.text_input("License File", value="license.dat")
    bind_info_file = st.text_input("Bind Info File", value="bind_info.json")
    run_mode = st.selectbox("Run Mode", ["streamlit", "api"])
    oauth2_introspect_url = st.text_input("OAuth2 introspect URL", value="https://your-auth-server.com/oauth2/introspect")
    oauth2_token_url = st.text_input("OAuth2 token URL", value="https://your-auth-server.com/oauth2/token")
    client_id = st.text_input("Client ID", value="your-client-id")
    client_secret = st.text_input("Client Secret", type="password", value="your-client-secret")

    login_btn = st.button("登录并启动")

    if login_btn:
        if not secret_key:
            st.error("Secret Key 不能为空")
            return
        if not license_file:
            st.error("License File 不能为空")
            return
        if not bind_info_file:
            st.error("Bind Info File 不能为空")
            return

        login_data = {
            "secret_key": secret_key,
            "license_file": license_file,
            "bind_info_file": bind_info_file,
            "run_mode": run_mode,
            "oauth2_introspect_url": oauth2_introspect_url,
            "oauth2_token_url": oauth2_token_url,
            "client_id": client_id,
            "client_secret": client_secret
        }

        # 保存到 session_state 和本地缓存文件
        st.session_state['login_params'] = login_data
        st.session_state['logged_in'] = True

        with open("login_cache.json", "w", encoding="utf-8") as f:
            json.dump(login_data, f)

        st.success("参数已保存，正在启动主程序...")
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    # 判断是否通过 streamlit run 启动
    if len(sys.argv) == 1 or "streamlit" in sys.argv[0].lower():
        # Web 模式
        if 'logged_in' not in st.session_state:
            st.session_state['logged_in'] = False

        # 自动读取本地缓存文件
        if not st.session_state['logged_in']:
            if os.path.exists("login_cache.json"):
                try:
                    with open("login_cache.json", "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    st.session_state['login_params'] = cached
                    st.session_state['logged_in'] = True
                except Exception as e:
                    st.error(f"读取缓存失败：{e}")
                    streamlit_login_page()
                    st.stop()
            else:
                streamlit_login_page()
                st.stop()

        # 构造 args
        args = argparse.Namespace(**st.session_state['login_params'])

    else:
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

    # 启动对应应用模式
    if args.run_mode == "streamlit":
        # 启动 Streamlit 应用
        app = Detection_UI(from_streamlit=True)
        app.setupMainWindow()
    elif args.run_mode == "api":
        # 运行 Flask API
        from api_server import socketio, app
        socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    else:
        print(f"Invalid RUN_MODE: {args.run_mode}. Please use 'streamlit' or 'api'.")
