import sys
import os
import argparse
import time
import os
import json
import streamlit as st
from check_license import check_license
from license_features import DEFAULT_FEATURES
from web import Detection_UI
from QtFusion.path import abs_path


# 设置环境变量以避免 OpenMP 错误
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["ENABLE_OAUTH"] = "FALSE"


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
        # 登录后重置成功提示标记
        st.session_state['license_message_shown'] = False

        with open("login_cache.json", "w", encoding="utf-8") as f:
            json.dump(login_data, f)

        st.success("参数已保存，正在启动主程序...")
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    # 设置页面布局为宽布局
    # 🚀 必须在第一行设置页面配置，在其他 Streamlit 命令之前
    st.set_page_config(
        page_title="光伏云组件检测系统",
        page_icon=abs_path("../icon/icon.jpg", path_type="current"),
        initial_sidebar_state="expanded",
        layout="wide",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': None
        }
    )

    # 判断是否通过 streamlit run 启动
    if len(sys.argv) == 1:
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
    ret, message, license_data = check_license(
        secret_key, args.license_file, args.bind_info_file
    )
    features = license_data.get("features", DEFAULT_FEATURES)
    os.environ["LICENSE_FEATURES"] = json.dumps(features, ensure_ascii=False)

    # 使用 st.empty() 创建占位符
    message_placeholder = st.empty()

    # 确保 session_state 中存在标记变量
    if len(sys.argv) == 1 and 'license_message_shown' not in st.session_state:
        st.session_state['license_message_shown'] = False

    if ret == 0:
        if len(sys.argv) == 1:
            # 仅在首次切换到主页面时显示成功消息
            if not st.session_state.get('license_message_shown', False):
                message_placeholder.success(f"Success: {message}")
                time.sleep(3)
                message_placeholder.empty()
                st.session_state['license_message_shown'] = True
        else:
            print(f"Success: {message}")
    else:
        if len(sys.argv) == 1:
            # 在占位符中显示错误消息
            message_placeholder.error(f"Error: {message}")
            # 等待 3 秒后清除消息
            time.sleep(3)
            message_placeholder.empty()
            st.stop()
        else:
            print(f"Error: {message}")
            sys.exit(1)

    # 设置环境变量以传递 OAuth2 配置
    os.environ["OAUTH2_INTROSPECT_URL"] = args.oauth2_introspect_url
    os.environ["OAUTH2_TOKEN_URL"] = args.oauth2_token_url
    os.environ["CLIENT_ID"] = args.client_id
    os.environ["CLIENT_SECRET"] = args.client_secret

    # 启动对应应用模式
    if args.run_mode == "streamlit":
        # 启动 Streamlit 应用
        app = Detection_UI(from_streamlit=True, enabled_features=features)
        app.setupMainWindow()
    elif args.run_mode == "api":
        # 运行 Flask API
        from api_server import socketio, app
        socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    else:
        print(f"Invalid RUN_MODE: {args.run_mode}. Please use 'streamlit' or 'api'.")
