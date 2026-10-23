import base64

import streamlit as st


def get_base64_of_bin_file(bin_file):
    """
    读取图片并转换为 Base64 编码格式
    """
    with open(bin_file, 'rb') as file:
        data = file.read()
    return base64.b64encode(data).decode()


def def_css_html():
    """
    定义 CSS 和 HTML 样式
    """
    st.markdown("""
        <style>
        /* 全局样式 */
        .css-2trqyj, .css-1d391kg, .st-bb, .st-at {
            font-family: 'Gill Sans', 'Gill Sans MT', Calibri, 'Trebuchet MS', sans-serif;
            background-color: #cadefc;
            color: #21618C;
        }

        /* 按钮样式 */
        .stButton > button {
            border: none;
            color: white;
            padding: 10px 20px; /* 减小 padding */
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px; /* 减小字体大小 */
            margin: 2px 1px; /* 调整边距 */
            cursor: pointer;
            border-radius: 8px; /* 调整边框圆角 */
            background-color: #9896f1;
            box-shadow: 0 2px 4px 0 rgba(0,0,0,0.2);
            transition-duration: 0.4s;
        }
        .stButton > button:hover {
            background-color: #5499C7;
            color: white;
            box-shadow: 0 8px 12px 0 rgba(0,0,0,0.24);
        }

        /* 侧边栏样式 */
        .css-1lcbmhc.e1fqkh3o0 {
            background-color: #154360;
            color: #FDFEFE;
            border-right: 2px solid #DDD;
        }

        /* Keep radio option labels wide enough for CJK text. Styling direct
           .stRadio children breaks newer Streamlit DOM layouts by shrinking
           the entire widget label to one character. */
        .stRadio [role="radiogroup"] {
            width: 100%;
        }
        .stRadio [role="radiogroup"] > label {
            display: flex;
            width: max-content;
            max-width: 100%;
            align-items: center;
        }
        .stRadio [role="radiogroup"] > label p {
            white-space: nowrap;
            overflow-wrap: normal;
            word-break: keep-all;
        }

        /* 滑块样式 */
        .stSlider .thumb {
            background-color: #2E86C1;
        }
        .stSlider .track {
            background-color: #DDD;
        }

        /* 全屏显示图标样式 */
        /* .fullscreen-button {
            filter: invert(1);
        } */

        /* 表格样式 */
        table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 18px;
            font-family: sans-serif;
            min-width: 400px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        thead tr {
            background-color: #a8d8ea;
            color: #ffcef3;
            text-align: left;
        }
        th, td {
            padding: 15px 18px;
        }
        tbody tr {
            border-bottom: 2px solid #ddd;
        }
        tbody tr:nth-of-type(even) {
            background-color: #D6EAF8;
        }
        tbody tr:last-of-type {
            border-bottom: 3px solid #5499C7;
        }
        tbody tr:hover {
            background-color: #AED6F1;
        }

        /* Streamlit 1.x uses stable data-testid attributes; the old generated
           .css-* selectors above change between releases and cannot control
           sidebar sizing reliably. */
        [data-testid="stSidebar"] {
            width: 380px;
            min-width: 360px;
            max-width: 420px;
        }
        [data-testid="stSidebar"] > div:first-child {
            width: 100%;
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;
            line-height: 1.35;
        }
        [data-testid="stSidebar"] [data-testid="stAlert"] {
            width: 100%;
            box-sizing: border-box;
            overflow-wrap: anywhere;
            white-space: normal;
        }
        [data-testid="stSidebar"] [data-baseweb="select"] {
            min-height: 42px;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"] {
            max-width: 100%;
        }
        [data-testid="stSidebar"] [data-baseweb="tag"] span {
            white-space: normal;
            overflow-wrap: anywhere;
        }
        @media (max-width: 900px) {
            [data-testid="stSidebar"] {
                min-width: 300px;
                max-width: 86vw;
            }
        }
        </style>
        """, unsafe_allow_html=True)
