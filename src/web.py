import random
import tempfile
import time
import os
import cv2
import json
import numpy as np
import pandas as pd
import streamlit as st
from QtFusion.path import abs_path
from QtFusion.utils import drawRectBox
from log import ResultLogger, LogTable
from model import Web_Detector
from chinese_name_list import EL_type, EL_class_colors, Thermo_type, Other_type, Thermo_class_colors, Visible_type, Visible_class_colors, Segmentation_type, Segmentation_class_colors, Other_class_colors
from ui_style import def_css_html
from utils import is_black_and_white, save_uploaded_file, concat_results, load_default_image, get_camera_names, draw_detections, save_chinese_image, format_time, convert_to_pseudo_colorizer, camera_undistortion, auto_undistort_image, rotate_image, auto_keystone_correction, enhance_texture, fill_largest_polygon_white
import tempfile
from datetime import datetime
from auth import verify_token, get_access_token
import tkinter as tk
from tkinter import filedialog
from utils import LocalFileObj
import base64
import hashlib
from functools import lru_cache
import threading
from concurrent.futures import ThreadPoolExecutor

# 🚀 性能优化模块导入
from streamlit_config import optimize_streamlit_performance, setup_image_optimization, add_performance_css

# 📝 命名配置模块导入
from naming_config import (
    get_image_type_name, get_task_type_name, get_export_format_name,
    generate_filename, get_status_message,
    SIDEBAR_HEADERS, BUTTON_TEXTS, SIDEBAR_HINTS, STATUS_MESSAGES, MAIN_LABELS,
    SYSTEM_CONFIG, SIDEBAR_OPTIONS, SIDEBAR_LABELS, MAIN_HEADERS, get_main_label
)
from image_optimizer import get_image_optimizer, optimize_image_display, process_uploaded_images


# 🚀 性能优化：添加缓存装饰器
@st.cache_data(ttl=300, max_entries=50)  # 缓存5分钟，最多50个条目
def cached_image_resize(image_bytes, width, height):
    """缓存图像调整大小操作"""
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    resized = cv2.resize(image, (width, height))
    return resized

@st.cache_data(ttl=600, max_entries=20)  # 缓存10分钟
def cached_image_processing(image_bytes, processing_params):
    """缓存图像预处理操作"""
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    
    # 根据参数进行处理
    if processing_params.get('enable_pseudo_color') and is_black_and_white(image):
        image = convert_to_pseudo_colorizer(
            image, 
            contrast=processing_params.get('contrast', 1.0),
            brightness=processing_params.get('brightness', 0)
        )
    
    if processing_params.get('enable_rotate_correction'):
        image = rotate_image(
            image,
            angle_x=processing_params.get('rot_angle_x', 0),
            angle_y=processing_params.get('rot_angle_y', 0),
            zoom_factor=processing_params.get('keystone_scale', 1.0)
        )
    
    return image

def generate_cache_key(*args):
    """生成缓存键"""
    content = str(args)
    return hashlib.md5(content.encode()).hexdigest()

# 尝试导入Git信息
try:
    from git_info import format_git_info_for_about, get_version_string
    GIT_INFO_AVAILABLE = True
except ImportError:
    GIT_INFO_AVAILABLE = False
    
    def format_git_info_for_about():
        return STATUS_MESSAGES["git_info_not_found"]
    
    def get_version_string():
        return STATUS_MESSAGES["unknown_version"]


class Detection_UI:
    """
    检测系统类。

    Attributes:
        model_type (str): 模型类型。
        conf_threshold (float): 置信度阈值。
        iou_threshold (float): IOU阈值。
        selected_camera (str): 选定的摄像头。
        uploaded_file (FileUploader): 上传的文件。
        detection_result (str): 检测结果。
        detection_location (str): 检测位置。
        detection_confidence (str): 检测置信度。
        detection_time (str): 检测用时。
    """

    def __init__(self, from_streamlit=False, api_params=None):
        """
        初始化光伏云组件检测系统的参数。
        """
        if from_streamlit and os.getenv("ENABLE_OAUTH") == "TRUE":
            CLIENT_ID = os.getenv("CLIENT_ID")
            CLIENT_SECRET = os.getenv("CLIENT_SECRET")
            OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL")

            # 验证环境变量是否存在
            if not OAUTH2_TOKEN_URL or not CLIENT_ID or not CLIENT_SECRET:
                st.error(
                    "Error: Missing required environment variables.\n"
                    "Please set the following variables:\n"
                    "  - OAUTH2_TOKEN_URL\n"
                    "  - CLIENT_ID\n"
                    "  - CLIENT_SECRET\n"
                )
                st.stop()

            # 获取 OAuth2 令牌
            access_token = get_access_token(OAUTH2_TOKEN_URL, CLIENT_ID, CLIENT_SECRET)
            if not access_token:
                st.error("Failed to retrieve ACCESS_TOKEN. Please check your credentials and token endpoint.")
                st.stop()

        self.from_streamlit = from_streamlit
        self.api_params = api_params or {}
        self.input_source = None
        self.rtsp_input_url = None
        self.enable_video_output = None
        self.output_path = abs_path("../output/")
        self.enable_rtsp_output = None
        self.rtsp_output_url = None

        # 🚀 性能优化：添加缓存管理
        self.image_cache = {}  # 图像缓存
        self.processing_cache = {}  # 处理结果缓存
        self.max_cache_size = 50  # 最大缓存条目数
        self.executor = ThreadPoolExecutor(max_workers=2)  # 异步处理线程池
        
        # 🚀 性能优化：设置 Streamlit 优化配置（不包含页面配置）
        if self.from_streamlit:
            # 只调用不包含 set_page_config 的优化函数
            optimize_streamlit_performance()
            add_performance_css()
            self.image_optimizer = get_image_optimizer()
        
        # 预设显示尺寸，避免重复计算
        self.display_width = 640
        self.display_height = 480

        # 初始化类别标签列表和为每个类别随机分配颜色
        self.cls_name = Visible_type
        self.detect_class_color = Visible_class_colors
        self.colors = [self.detect_class_color.get(class_name, (0, 255, 0)) for class_name in self.cls_name.values()]
        self.selected_class_ids = None  # 选定的类别索引

        # 设置页面标题
        self.title = SYSTEM_CONFIG["title"]
        if self.from_streamlit:
            self.setup_page()  # 初始化页面布局
            def_css_html()  # 应用 CSS 样式

        # Define the path to the logo
        logo_path = abs_path("../icon/logo.jpg", path_type="current")

        # Check if the logo file exists
        if os.path.exists(logo_path):
            # Use markdown to center the image
            st.markdown(
                f"""
                <div style="text-align: center;">
                    <img src="data:image/jpeg;base64,{base64.b64encode(open(logo_path, "rb").read()).decode()}" width="500">
                </div>
                """,
                unsafe_allow_html=True
            )

        # 初始化检测相关的配置参数
        self.model_type = SYSTEM_CONFIG["model_type_detection"]
        self.conf_threshold = 0.15  # 默认置信度阈值
        self.iou_threshold = 0.5  # 默认IOU阈值
        self.image_type = SYSTEM_CONFIG["image_type_visible"]  # 图像类型

        # 初始化检测类别相关的配置参数
        self.available_classes = None  # 可用的检测类别
        self.available_class_keys = None # 可用的检测类别键
        self.selected_classes = list(self.cls_name.keys())  # 选定的检测类别

        # 初始化相机和文件相关的变量
        self.selected_camera = None
        self.uploaded_file = None
        self.uploaded_video = None
        self.custom_model_file = None  # 自定义的模型文件

        # 初始化黑白图片转换为伪彩色相关的变量
        self.enable_pseudo_color = False
        self.image_contrast = 1.0
        self.image_brightness = 0.0
        self.enable_rotate_correction = False  # 启用旋转校正
        self.enable_auto_keystone_correction = False  # 启用自动梯形校正
        self.enable_background_fill = False  # 启用背景填充
        self.rot_angle_x = 0  # 垂直旋转角度
        self.rot_angle_y = 0  # 水平旋转角度
        self.keystone_scale = 1.0  # 缩放比例
        self.scale_factor_keystone = 0.1  # 自动梯形校正的最小面积比例
        self.scale_factor_fill = 0.1  # 背景填充的最小面积比例
        self.image_enhancement_method = SYSTEM_CONFIG["image_enhancement_none"]  # 图像增强方法

        # 初始化检测结果相关的变量
        self.detection_result = None
        self.detection_location = None
        self.detection_confidence = None
        self.detection_time = None

        # 初始化分割结果输出相关的变量
        self.rectangle_bounding_output = True

        # 初始化UI显示相关的变量（仅Streamlit）
        self.display_mode = None  # 设置显示模式
        self.close_flag = None  # 控制图像显示结束的标志
        self.close_placeholder = st.empty()  # 关闭按钮区域
        self.image_placeholder = None  # 用于显示图像的区域
        self.image_placeholder_res = None  # 图像显示区域
        self.table_placeholder = None  # 表格显示区域
        self.log_table_placeholder = None  # 完整结果表格显示区域
        self.selectbox_placeholder = None  # 下拉框显示区域
        self.selectbox_target = None  # 下拉框选中项
        self.progress_bar = None  # 用于显示的进度条
        self.export_format = 'CSV'  # 导出格式

        self.frame_count_placeholder = None  # 帧计数显示区域
        self.fps_placeholder = None  # FPS显示区域
        self.target_count_placeholder = None  # 目标计数显示区域
        self.detection_time_placeholder = None  # 检测时间显示区域
        self.selectbox_placeholder = None

        self.new_width = 1080
        self.new_height = int(self.new_width * (9 / 16))

        # 初始化FPS和视频时间指针
        self.FPS = 30
        self.timenow = 0

        # 初始化相机参数
        self.undistortion_method = SYSTEM_CONFIG["undistortion_none"]
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_file = None
        self.image_k1 = 0.0  # 畸变系数

        self.csv_output_path = abs_path("../output/logs/", path_type="current")
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 初始化日志数据保存路径
        self.saved_log_data = os.path.join(self.csv_output_path, f"log_table_data_{current_time}.csv")

        # 初始化
        self.available_cameras = get_camera_names()
        self.logTable = LogTable(self.saved_log_data)
        self.model = Web_Detector()
        self.colors = []

        # 确保 logTable 属性始终存在
        if not hasattr(self, 'logTable'):
            self.logTable = LogTable(self.saved_log_data)

        if 'current_frame_count' not in st.session_state:
            st.session_state['current_frame_count'] = 0
        if 'current_fps' not in st.session_state:
            st.session_state['current_fps'] = 0
        if 'current_target_count' not in st.session_state:
            st.session_state['current_target_count'] = 0
        if 'current_detection_time' not in st.session_state:
            st.session_state['current_detection_time'] = 0

        if 'saved_images_ini' not in st.session_state:
            # 初始化保存的原始图像列表
            st.session_state['saved_images_ini'] = []
        if 'saved_images' not in st.session_state:
            # 初始化保存的结果图像列表
            st.session_state['saved_images'] = []
        if 'saved_names' not in st.session_state:
            # 初始化保存的图像名称列表
            st.session_state['saved_names'] = []

        if self.from_streamlit:
            self.setup_sidebar()  # 初始化侧边栏布局
        else:
            self.load_api_params()  # 加载API参数

    def load_api_params(self):
        """
        用于 Flask 模式，根据 API 提供的参数设置实例变量。
        """
        # 根据 API 提供的参数设置实例变量
        self.csv_output_path = self.api_params.get("csv_output_path", abs_path("../output/logs/", path_type="current"))

        # 确保路径以斜杠结尾
        if not self.csv_output_path.endswith(os.sep):
            self.csv_output_path += os.sep

        # 根据用户输入的路径设置日志文件路径
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.saved_log_data = os.path.join(self.csv_output_path, f"log_table_data_{current_time}.csv")

        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(self.csv_output_path):
            os.makedirs(self.csv_output_path)

        self.available_cameras = get_camera_names()
        self.logTable = LogTable(self.saved_log_data)
        self.model = Web_Detector()

        self.conf_threshold = float(self.api_params.get("conf_threshold", 0.15))
        self.iou_threshold = float(self.api_params.get("iou_threshold", 0.25))
        self.model_type = self.api_params.get("model_type", SYSTEM_CONFIG["model_type_detection"])
        self.image_type = self.api_params.get("image_type", SYSTEM_CONFIG["image_type_visible"])
        self.selected_classes = self.api_params.get("selected_classes", list(Visible_type.keys()))
        self.enable_pseudo_color = self.api_params.get("enable_pseudo_color", False)
        self.enable_rotate_correction = self.api_params.get("enable_rotate_correction", False)
        self.enable_auto_keystone_correction = self.api_params.get("enable_auto_keystone_correction", False)
        self.enable_background_fill = self.api_params.get("enable_background_fill", False)
        self.image_enhancement_method = self.api_params.get("image_enhancement_method", SYSTEM_CONFIG["image_enhancement_none"])
        self.undistortion_method = self.api_params.get("undistortion_method", SYSTEM_CONFIG["undistortion_none"])

        # 通过API方式上传相机标定文件
        if self.undistortion_method == SYSTEM_CONFIG["undistortion_camera_calc"]:
            calibration_file = self.api_params.get("calibration_file", None)
            if calibration_file is not None:
                try:
                    # calibration_file 可以是文件路径或文件内容
                    if isinstance(calibration_file, str) and os.path.exists(calibration_file):
                        with open(calibration_file, "r", encoding="utf-8") as f:
                            calib_data = json.load(f)
                    else:
                        # 假设是文件内容（字典或JSON字符串）
                        if isinstance(calibration_file, dict):
                            calib_data = calibration_file
                        else:
                            calib_data = json.loads(calibration_file)
                    self.camera_matrix = np.array(calib_data["camera_matrix"])
                    self.dist_coeffs = np.array(calib_data["dist_coeffs"])
                    self.calibration_file = calibration_file if isinstance(calibration_file, str) else "api_upload"
                    print(STATUS_MESSAGES["camera_calibration_success"])
                except Exception as e:
                    print(get_status_message("camera_calibration_failed", error=str(e)))
                    self.camera_matrix = None
                    self.dist_coeffs = None
                    self.calibration_file = None
            else:
                self.camera_matrix = None
                self.dist_coeffs = None
                self.calibration_file = None
        elif self.undistortion_method == SYSTEM_CONFIG["undistortion_manual"]:
            # 从API参数中获取畸变系数
            self.image_k1 = float(self.api_params.get("image_k1", 0.0))
        
        if self.enable_pseudo_color:
            self.image_contrast = float(self.api_params.get("image_contrast", 1.0))
            self.image_brightness = float(self.api_params.get("image_brightness", 0.0))

        if self.enable_rotate_correction:
            self.rot_angle_x = float(self.api_params.get("rot_angle_x", 0))
            self.rot_angle_y = float(self.api_params.get("rot_angle_y", 0))
            self.keystone_scale = float(self.api_params.get("keystone_scale", 1.0))

        if self.enable_auto_keystone_correction:
            self.scale_factor_keystone = float(self.api_params.get("scale_factor_keystone", 0.1))
        
        if self.enable_background_fill:
            self.scale_factor_fill = float(self.api_params.get("scale_factor_fill", 0.1))

        # 设置类别标签
        if self.model_type == SYSTEM_CONFIG["model_type_segmentation"]:
            self.cls_name = Segmentation_type
            self.detect_class_color = Segmentation_class_colors
        else:
            if self.image_type == SYSTEM_CONFIG["image_type_thermal"]:
                self.cls_name = Thermo_type
                self.detect_class_color = Thermo_class_colors
            elif self.image_type == SYSTEM_CONFIG["image_type_el"]:
                self.cls_name = EL_type
                self.detect_class_color = EL_class_colors
            elif self.image_type == "可见光":
                self.cls_name = Visible_type
                self.detect_class_color = Visible_class_colors
            else:
                self.cls_name = Other_type
                self.detect_class_color = Other_class_colors

        # 重新加载模型
        if self.model_type == "检测任务":
            if self.image_type == "红外":
                model_path = abs_path("../weights/yolo11s-thermo.pt", path_type="current")
            elif self.image_type == "EL隐裂":
                model_path = abs_path("../weights/yolo11s-el.pt", path_type="current")
            elif self.image_type == "可见光":
                model_path = abs_path("../weights/yolo11s-visible.pt", path_type="current")
            else:
                model_path = abs_path("../weights/yolo11s.pt", path_type="current")
        else:
            if self.image_type == "红外":
                model_path = abs_path("../weights/yolo11s-thermo-seg.pt", path_type="current")
            elif self.image_type == "可见光":
                model_path = abs_path("../weights/yolo11s-visible-seg.pt", path_type="current")
            else:
                print("Invalid image type for segmentation task.")

        try:
            self.model.load_model(model_path=model_path)
            # 确保类别排序一致
            sorted_cls_name = {name: self.cls_name[name] for name in self.model.names if name in self.cls_name}
            self.cls_name = sorted_cls_name

            # 重新初始化颜色列表，确保顺序与模型类别一致
            for class_name in self.model.names:
                if class_name in self.detect_class_color:
                    # 如果已定义颜色，使用定义的颜色
                    self.colors.append(self.detect_class_color[class_name])
                else:
                    # 如果未定义颜色，填充随机颜色
                    self.colors.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

            # 确保颜色列表长度与模型类别一致
            if len(self.colors) != len(self.model.names):
                st.warning(STATUS_MESSAGES["color_list_warning"])

        except Exception as e:
            print(f"无法加载模型文件，请检查文件路径或文件是否存在！错误信息: {str(e)}")

    def setup_page(self):
        """
        设置 Streamlit 页面标题和布局。
        """
        # 居中显示标题
        st.markdown(
            f'<h1 style="text-align: center;">{self.title}</h1>',
            unsafe_allow_html=True
        )

    def show_about_section(self):
        """
        在 Streamlit UI 的右上角显示关于部分。
        """
        # 获取版本信息字符串
        version_string = get_version_string()

        with st.sidebar.expander(SIDEBAR_LABELS["about_version"].format(version_string=version_string), expanded=False):
            st.markdown("""
                ## 关于本应用
                本应用旨在检测光伏组件的故障，包括：
                - 可见光故障
                - 红外热故障
                - EL隐裂
                - 其他异常（如异物入侵）

                ### 功能特点：
                - 使用摄像头或 RTSP/RTMP 流进行实时检测
                - 批量处理图片和视频
                - 高级图像校正技术（例如：畸变校正、梯形校正）
                - 支持多种格式导出检测结果（CSV、Excel、JSON、Word）

                ### 使用技术：
                - **Streamlit** 用于用户界面
                - **OpenCV** 用于图像处理
                - **YOLOv11** 用于目标检测
                - **NumPy** 用于数值计算
            """)
            
            # 显示Git版本信息
            if GIT_INFO_AVAILABLE:
                st.markdown("---")
                git_info_md = format_git_info_for_about()
                st.markdown(git_info_md)
            
            st.markdown("""
                ---
                ### 作者：
                由 Phillweston 开发。

                ### 联系方式：
                如有疑问或需要支持，请联系：lrt2443655975@gmail.com
            """)

    def setup_sidebar(self):
        """
        设置 Streamlit 侧边栏。

        在侧边栏中配置模型设置、摄像头选择以及识别项目设置等选项。
        """
        st.sidebar.title(SIDEBAR_HEADERS["settings_menu"])

        # Add the About section to the sidebar
        self.show_about_section()

        # 添加登录设置
        st.sidebar.header(SIDEBAR_HEADERS["login_settings"])
        if st.sidebar.button(SIDEBAR_LABELS["logout_button"]):
            st.session_state.clear()
            if os.path.exists("login_cache.json"):
                os.remove("login_cache.json")
            st.rerun()

        # 添加显示设置
        st.sidebar.header(SIDEBAR_HEADERS["display_settings"])

        # 添加固定比例选项
        aspect_ratio = st.sidebar.selectbox(SIDEBAR_LABELS["aspect_ratio_selection"], options=SIDEBAR_OPTIONS["aspect_ratios"], index=0)
        if aspect_ratio == "16:9":
            ratio = 16 / 9
        elif aspect_ratio == "4:3":
            ratio = 4 / 3
        else:
            ratio = None  # 自由调整

        # 根据选择的比例调整宽度和高度
        if ratio:
            # 用户输入高度时自动调整宽度
            self.new_height = st.sidebar.number_input(SIDEBAR_LABELS["display_height_input"], min_value=100, max_value=2160, value=1080, step=10)
            self.new_width = int(self.new_height * ratio)
            st.sidebar.number_input(SIDEBAR_LABELS["display_width_input"], value=self.new_width, disabled=True)
        else:
            # 自由调整模式
            self.new_width = st.sidebar.number_input(SIDEBAR_LABELS["display_width_input_free"], min_value=100, max_value=3840, value=1080, step=10)
            self.new_height = st.sidebar.number_input(SIDEBAR_LABELS["display_height_input_free"], min_value=100, max_value=2160, value=720, step=10)

        # 添加 CSV 输出路径设置
        st.sidebar.header(SIDEBAR_HEADERS["log_path_settings"])
        self.csv_output_path = st.sidebar.text_input(
            SIDEBAR_LABELS["log_save_path"],
            value=abs_path("../output/logs", path_type="current"),  # 默认路径
            placeholder="例如：D:/output/logs"
        )

        # 确保路径以斜杠结尾
        if not self.csv_output_path.endswith(os.sep):
            self.csv_output_path += os.sep

        st.sidebar.header(SIDEBAR_HEADERS["export_format_settings"])
        self.export_format = st.sidebar.radio(SIDEBAR_LABELS["export_format_selection"], options=SIDEBAR_OPTIONS["export_formats"], index=0)
        st.sidebar.caption(SIDEBAR_HINTS["export_format_hint"].format(format=self.export_format, path=self.csv_output_path))

        # 根据用户选择的导出格式设置文件后缀
        if self.export_format == "CSV":
            file_suffix = ".csv"
        elif self.export_format == "Excel":
            file_suffix = ".xlsx"
        elif self.export_format == "JSON":
            file_suffix = ".json"
        elif self.export_format == "Word":
            file_suffix = ".docx"
        else:
            file_suffix = ".txt"

        # 根据用户输入的路径设置日志文件路径
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.saved_log_data = os.path.join(self.csv_output_path, f"log_table_data_{current_time}{file_suffix}")

        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(self.csv_output_path):
            os.makedirs(self.csv_output_path)

        # Streamlit模式初始化 session state
        if 'logTable' not in st.session_state:
            # 如果在 session state 中不存在logTable，创建一个新的LogTable实例
            st.session_state['logTable'] = LogTable(self.saved_log_data)
        if 'available_cameras' not in st.session_state:
            # 获取或更新可用摄像头列表
            st.session_state['available_cameras'] = get_camera_names()
        if 'model' not in st.session_state:
            # 加载或创建模型实例
            st.session_state['model'] = Web_Detector()

        self.available_cameras = st.session_state['available_cameras']
        if len(self.available_cameras) == 1:
            st.write(STATUS_MESSAGES["no_camera_found"])

        # 初始化或获取识别结果的表格
        self.logTable = st.session_state['logTable']
        self.model = st.session_state['model']

        st.sidebar.header(SIDEBAR_HEADERS["detection_thresholds"])
        # 置信度阈值的滑动条
        self.conf_threshold = float(st.sidebar.slider(SIDEBAR_LABELS["conf_threshold_slider"], min_value=0.0, max_value=1.0, value=0.15))
        st.sidebar.caption(SIDEBAR_HINTS["conf_threshold_hint"])
        # IOU阈值的滑动条
        self.iou_threshold = float(st.sidebar.slider(SIDEBAR_LABELS["iou_threshold_slider"], min_value=0.0, max_value=1.0, value=0.25))
        st.sidebar.caption(SIDEBAR_HINTS["iou_threshold_hint"])
        # 设置侧边栏的模型设置部分
        st.sidebar.header(SIDEBAR_HEADERS["model_settings"])
        # 选择模型类型的下拉菜单
        self.model_type = st.sidebar.radio(SIDEBAR_LABELS["task_type_selection"], options=SIDEBAR_OPTIONS["task_types"], index=0)

        available_options = []
        # 添加提示信息
        if self.model_type == "检测任务":
            st.sidebar.caption(SIDEBAR_HINTS["detection_task_hint"])
            # 检测任务也应该有矩形框选项
            self.rectangle_bounding_output = st.sidebar.checkbox(SIDEBAR_LABELS["rectangle_output_checkbox"], value=True)
            available_options = ["EL隐裂", "红外", "可见光", "其他"]
        elif self.model_type == "分割任务":
            self.rectangle_bounding_output = st.sidebar.checkbox(SIDEBAR_LABELS["rectangle_output_checkbox"], value=True)
            st.sidebar.caption(SIDEBAR_HINTS["segmentation_task_hint"])
            available_options = ["红外", "可见光"]

        # 添加图像类型选择
        st.sidebar.header(SIDEBAR_HEADERS["image_type_selection"])
        self.image_type = st.sidebar.radio(
            SIDEBAR_LABELS["select_image_type"],
            options=available_options,
            index=0  # 默认选择第一个选项
        )

        if self.model_type == "检测任务":
            if self.image_type == "红外":
                self.cls_name = Thermo_type
                self.detect_class_color = Thermo_class_colors
            elif self.image_type == "EL隐裂":
                self.cls_name = EL_type
                self.detect_class_color = EL_class_colors
            elif self.image_type == "可见光":
                self.cls_name = Visible_type
                self.detect_class_color = Visible_class_colors
            else:
                self.cls_name = Other_type
                self.detect_class_color = Other_class_colors
        elif self.model_type == "分割任务":
            self.cls_name = Segmentation_type
            self.detect_class_color = Segmentation_class_colors

        # 提示用户选择的图像类型
        st.sidebar.caption(SIDEBAR_HINTS["image_type_hint"])

        # 设置侧边栏的选择需要检测的目标类别部分，默认选择所有类别
        st.sidebar.header(SIDEBAR_HEADERS["target_class_selection"])
        self.available_classes = list(self.cls_name.values())
        self.available_class_keys = list(self.cls_name.keys())
        selected_chinese_classes = st.sidebar.multiselect(
            SIDEBAR_LABELS["select_detection_or_segmentation_type"],
            options=self.available_classes,
            default=self.available_classes  # 默认选择所有类别
        )

        # 将选定的类别转换为索引
        self.selected_class_ids = [
            idx for idx, name in enumerate(self.model.names) if name in selected_chinese_classes
        ]

        # 添加提示信息
        if len(selected_chinese_classes) == 0:
            st.sidebar.caption(SIDEBAR_HINTS["no_class_selected_hint"])
        else:
            st.sidebar.caption(SIDEBAR_HINTS["selected_classes_hint"].format(classes=', '.join(selected_chinese_classes)))

        # 正确映射中文名称到英文名称
        self.selected_classes = [
            english_name for english_name, chinese_name in self.cls_name.items() 
            if chinese_name in selected_chinese_classes
        ]

        # 选择模型文件类型，可以是默认的或者自定义的
        st.sidebar.header(SIDEBAR_HEADERS["model_file_settings"])
        model_file_option = st.sidebar.radio(SIDEBAR_LABELS["model_settings"], options=SIDEBAR_OPTIONS["model_settings"], index=0)
        if model_file_option == "指定权重文件":
            # 如果选择自定义模型文件，则提供文件上传器
            model_file = st.sidebar.file_uploader(SIDEBAR_LABELS["select_pt_file"], type="pt")

            # 如果上传了模型文件，则保存并加载该模型
            if model_file is not None:
                self.custom_model_file = save_uploaded_file(model_file)
                try:
                    self.model.load_model(model_path=self.custom_model_file)
                except Exception as e:
                    st.sidebar.error(STATUS_MESSAGES["model_load_error"].format(error=str(e)))
                # 检查模型类别是否与选定类别一致
                if set(self.model.names) != set(self.available_class_keys):
                    st.sidebar.error(STATUS_MESSAGES["model_class_mismatch"])
                else:
                    self.colors = [self.detect_class_color.get(class_name, (0, 255, 0)) for class_name in self.cls_name.values()]
        elif model_file_option == "默认":
            if self.model_type == "检测任务":
                if self.image_type == "红外":
                    model_path=abs_path("../weights/yolo11s-thermo.pt", path_type="current")
                elif self.image_type == "EL隐裂":
                    model_path=abs_path("../weights/yolo11s-el.pt", path_type="current")
                elif self.image_type == "可见光":
                    model_path=abs_path("../weights/yolo11s-visible.pt", path_type="current")
                else:
                    model_path=abs_path("../weights/yolo11s.pt", path_type="current")
            else:
                if self.image_type == "红外":
                    model_path=abs_path("../weights/yolo11s-thermo-seg.pt", path_type="current")
                elif self.image_type == "可见光":
                    model_path=abs_path("../weights/yolo11s-visible-seg.pt", path_type="current")
                else:
                    st.sidebar.error(STATUS_MESSAGES["unsupported_image_type"])

            try:
                self.model.load_model(model_path=model_path)
                # 确保类别排序一致
                sorted_cls_name = {name: self.cls_name[name] for name in self.model.names if name in self.cls_name}
                self.cls_name = sorted_cls_name

                # 重新初始化颜色列表，确保顺序与模型类别一致
                for class_name in self.model.names:
                    if class_name in self.detect_class_color:
                        # 如果已定义颜色，使用定义的颜色
                        self.colors.append(self.detect_class_color[class_name])
                    else:
                        # 如果未定义颜色，填充随机颜色
                        self.colors.append((random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

                # 确保颜色列表长度与模型类别一致
                if len(self.colors) != len(self.model.names):
                    st.warning(STATUS_MESSAGES["color_list_warning"])

            except Exception as e:
                st.sidebar.error(STATUS_MESSAGES["default_model_load_error"].format(error=str(e)))

            # 检查类别是否完全一致
            if set(self.model.names) != set(self.available_class_keys):
                # 如果 chinese_name_list 的类别比模型的类别少，则以 chinese_name_list 为准
                if len(self.available_class_keys) < len(self.model.names):
                    self.model.names = [name for name in self.model.names if name in self.available_class_keys]
                # 如果 chinese_name_list 的类别比模型的类别多，则以模型为准
                else:
                    self.available_class_keys = [key for key in self.available_class_keys if key in self.model.names]

                # 重新检查类别是否一致
                missing_in_model = set(self.available_class_keys) - set(self.model.names)
                missing_in_selected = set(self.model.names) - set(self.available_class_keys)

                # 输出缺失的类别
                print(f"模型类别: {self.model.names}")
                print(f"选定类别: {self.available_class_keys}")
                print(f"模型中缺失的类别: {missing_in_model}")
                print(f"选定类别中缺失的类别: {missing_in_selected}")

                # 在 Streamlit 侧边栏显示错误信息
                st.sidebar.warning(STATUS_MESSAGES["model_class_auto_adjusted"])
            else:
                # 为模型中的类别重新分配颜色
                self.colors = [
                    self.detect_class_color.get(class_name, [random.randint(0, 255) for _ in range(3)])
                    for class_name in self.model.names
                ]

        # 设置侧边栏的摄像头和 RTSP/RTMP 配置部分
        st.sidebar.header(SIDEBAR_HEADERS["input_source_settings"])
        # 选择输入源类型：无输入，摄像头或 RTSP/RTMP 流
        self.input_source = st.sidebar.radio(SIDEBAR_LABELS["input_source_selection"], options=SIDEBAR_OPTIONS["input_sources"], index=0)

        if "file_key" not in st.session_state:
            st.session_state["file_key"] = str(random.random())

        if self.input_source == "摄像头":
            # 选择摄像头的下拉菜单
            self.selected_camera = st.sidebar.selectbox(SIDEBAR_LABELS["camera_selection"], self.available_cameras)
            st.sidebar.caption(SIDEBAR_HINTS["camera_hint"])
        elif self.input_source == "RTSP/RTMP流":
            # 输入 RTSP/RTMP 地址
            self.rtsp_input_url = st.sidebar.text_input(SIDEBAR_LABELS["rtsp_input"], placeholder="例如：rtsp://<ip>:<port>/path 或 rtmp://<ip>:<port>/path")
            st.sidebar.caption(SIDEBAR_HINTS["rtsp_hint"])
        elif self.input_source == "图片文件":
            self.uploaded_file = st.sidebar.file_uploader(SIDEBAR_LABELS["upload_images"], type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=st.session_state["file_key"])
            
            # 显示上传状态和进度
            if self.uploaded_file:
                num_files = len(self.uploaded_file)
                st.sidebar.success(SIDEBAR_HINTS["image_upload_success"].format(count=num_files))
                
                # 显示文件列表
                with st.sidebar.expander(SIDEBAR_LABELS["display_uploaded_files"], expanded=False):
                    for i, file in enumerate(self.uploaded_file[:10]):  # 最多显示前10个
                        file_size = len(file.getvalue()) / 1024  # KB
                        st.write(f"{i+1}. {file.name} ({file_size:.1f} KB)")
                    if num_files > 10:
                        st.write(SIDEBAR_HINTS["more_files_remaining"].format(count=num_files - 10))
            else:
                st.sidebar.info(SIDEBAR_HINTS["image_upload_hint"])
                
            st.sidebar.caption(SIDEBAR_HINTS["image_detection_hint"])
        elif self.input_source == "图片文件夹":
            default_types = ["jpg", "jpeg", "png"]
            image_types = st.sidebar.multiselect(
                SIDEBAR_LABELS["select_image_type"], 
                options=["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"], 
                default=default_types
            )

            # Tkinter文件夹选择器按钮
            if st.sidebar.button(SIDEBAR_LABELS["select_image_folder"]):
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                folder_path = filedialog.askdirectory(master=root)
                root.destroy()
                if folder_path:
                    st.session_state['image_folder_path'] = folder_path

            folder_path = st.sidebar.text_input(
                SIDEBAR_LABELS["input_folder_path"], 
                value=st.session_state.get('image_folder_path', ''), 
                placeholder="例如：D:/images"
            )
            image_files = []
            if folder_path and os.path.isdir(folder_path):
                # 显示扫描进度
                with st.sidebar:
                    st.info(STATUS_MESSAGES["scanning_folder"])
                    scan_progress = st.progress(0)
                    
                exts = tuple(f".{ext.lower()}" for ext in image_types)
                total_dirs = sum([len(dirs) for _, dirs, _ in os.walk(folder_path)]) + 1
                current_dir = 0
                
                for root_dir, dirs, files in os.walk(folder_path):
                    current_dir += 1
                    scan_progress.progress(current_dir / total_dirs)
                    
                    for file in files:
                        if file.lower().endswith(exts):
                            image_files.append(os.path.join(root_dir, file))
                
                scan_progress.progress(1.0)
                st.sidebar.success(SIDEBAR_HINTS["scanning_complete"].format(count=len(image_files)))

                # 显示文件夹统计信息
                if image_files:
                    with st.sidebar.expander(SIDEBAR_LABELS["folder_statistics"], expanded=False):
                        # 按文件类型统计
                        type_count = {}
                        for file in image_files:
                            ext = os.path.splitext(file)[1].lower()
                            type_count[ext] = type_count.get(ext, 0) + 1
                        
                        st.write("按类型统计:")
                        for ext, count in type_count.items():
                            st.write(f"  {ext}: {count} 张")
                        
                        # 显示前几个文件名
                        st.write("示例文件:")
                        for i, file in enumerate(image_files[:5]):
                            st.write(f"  {i+1}. {os.path.basename(file)}")
                        if len(image_files) > 5:
                            st.write(SIDEBAR_HINTS["more_files_remaining"].format(count=len(image_files) - 5))
                
                # 转为文件对象
                self.uploaded_file = [LocalFileObj(f) for f in image_files]
            else:
                if folder_path:
                    st.sidebar.error(SIDEBAR_HINTS["invalid_folder_path"])
                st.sidebar.caption(SIDEBAR_HINTS["folder_selection_hint"])
                self.uploaded_file = []
        elif self.input_source == "视频文件":
            self.uploaded_video = st.sidebar.file_uploader(SIDEBAR_LABELS["upload_videos"], type=["mp4", "avi", "mov"], accept_multiple_files=True, key=st.session_state["file_key"])
            
            # 显示上传状态和进度
            if self.uploaded_video:
                num_videos = len(self.uploaded_video)
                st.sidebar.success(SIDEBAR_HINTS["video_upload_success"].format(count=num_videos))
                
                # 显示视频列表和信息
                with st.sidebar.expander(SIDEBAR_LABELS["display_uploaded_video"], expanded=False):
                    total_size = 0
                    for i, video in enumerate(self.uploaded_video[:5]):  # 最多显示前5个
                        video_size = len(video.getvalue()) / (1024 * 1024)  # MB
                        total_size += video_size
                        st.write(f"{i+1}. {video.name} ({video_size:.1f} MB)")
                    if num_videos > 5:
                        st.write(STATUS_MESSAGES["more_videos_remaining"].format(count=num_videos - 5))
                    st.write(SIDEBAR_HINTS["total_size"].format(size=total_size))
            else:
                st.sidebar.info(SIDEBAR_HINTS["video_upload_hint"])
                
            st.sidebar.caption(SIDEBAR_HINTS["video_detection_hint"])
        elif self.input_source == "视频文件夹":
            default_video_types = ["mp4", "avi", "mov"]
            video_types = st.sidebar.multiselect(
                SIDEBAR_LABELS["select_video_type"],
                options=["mp4", "avi", "mov", "mkv", "flv", "wmv"],
                default=default_video_types
            )
            # Tkinter文件夹选择器按钮
            if st.sidebar.button(SIDEBAR_LABELS["select_video_folder"]):
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                folder_path = filedialog.askdirectory(master=root)
                root.destroy()
                if folder_path:
                    st.session_state['video_folder_path'] = folder_path

            folder_path = st.sidebar.text_input(
                "输入视频文件夹路径",
                value=st.session_state.get('video_folder_path', ''),
                placeholder="例如：D:/videos"
            )
            video_files = []
            if folder_path and os.path.isdir(folder_path):
                exts = tuple(f".{ext.lower()}" for ext in video_types)
                for root_dir, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(exts):
                            video_files.append(os.path.join(root_dir, file))
                st.sidebar.write(f"📂 共找到视频数量: {len(video_files)}")
                # 转为文件对象
                self.uploaded_video = [LocalFileObj(f) for f in video_files]
            else:
                st.sidebar.caption("💡 提示: 选择或输入本地视频文件夹路径，自动递归查找所有视频。")
                self.uploaded_video = []

        # 清空按钮
        if st.sidebar.button("🗑️ 清空已上传文件"):
            self.uploaded_file = None
            self.uploaded_video = None

            # 清空 file_uploader 的 key 以强制刷新组件
            st.session_state["file_key"] = str(random.random())

            # 清理与 file_uploader 有关的 session state
            for key in list(st.session_state.keys()):
                if key.startswith("file_uploader"):
                    del st.session_state[key]

            # 清空文件夹路径（图片/视频）
            if 'image_folder_path' in st.session_state:
                del st.session_state['image_folder_path']
            if 'video_folder_path' in st.session_state:
                del st.session_state['video_folder_path']

            # 显式设置文件对象为空（用于 LocalFileObj 列表）
            self.uploaded_file = []
            self.uploaded_video = []

            # 重新运行 Streamlit 应用以更新状态
            st.rerun()

            st.sidebar.success("已清空所有上传的文件！")

        if self.input_source in ["摄像头", "RTSP/RTMP流", "视频文件"]:
            # 添加视频输出和 RTSP 输出的启用复选框
            st.sidebar.header("🎥 视频输出设置")
            self.enable_video_output = st.sidebar.checkbox("启用视频输出", value=True)

        # 图像畸变校正参数设置
        st.sidebar.header("🖼️ 输入图像或视频处理")
        # 添加伪彩色转换选项
        self.enable_pseudo_color = st.sidebar.checkbox("启用伪彩色转换", value=False)
        st.sidebar.caption("💡 提示: 伪彩色转换针对于输入图像为黑白图像且图像类型为红外热图。")
        # 如果启用伪彩色转换，显示对比度和亮度调整选项
        if self.enable_pseudo_color:
            self.image_contrast = st.sidebar.slider("对比度调整", min_value=0.5, max_value=3.0, value=1.0, step=0.1)
            self.image_brightness = st.sidebar.slider("亮度调整", min_value=-255, max_value=255, value=0, step=1)

        # 添加图像旋转校正选项
        self.enable_rotate_correction = st.sidebar.checkbox("启用图像旋转校正", value=False)
        if self.enable_rotate_correction:
            # 滑动条调整水平和垂直旋转角度，以及缩放比例
            self.rot_angle_x = st.sidebar.slider("垂直旋转角度（绕X轴）", min_value=-90, max_value=90, value=0, step=1)
            self.rot_angle_y = st.sidebar.slider("水平旋转角度（绕Y轴）", min_value=-90, max_value=90, value=0, step=1)
            self.keystone_scale = st.sidebar.slider("缩放比例", min_value=0.5, max_value=2.0, value=1.0, step=0.01)
        st.sidebar.caption("💡 提示: 图像旋转校正用于修正图像的倾斜角度，适用于拍摄角度不正的图像。")

        # 添加梯形校正选项
        self.enable_auto_keystone_correction = st.sidebar.checkbox("启用自动梯形校正", value=False)
        if self.enable_auto_keystone_correction:
            # 滑动条调整最小面积比例
            self.scale_factor_keystone = st.sidebar.slider("梯形校正轮廓检测最小面积比例 ", min_value=0.1, max_value=0.8, value=0.1, step=0.05)
        st.sidebar.caption("💡 提示: 梯形校正用于修正图像的透视畸变，适用于拍摄角度不正的图像。目前仅适用于EL图像检测。")

        # 添加背景填充选项
        self.enable_background_fill = st.sidebar.checkbox("启用自动背景填充", value=False)
        if self.enable_background_fill:
            # 滑动条调整最小面积比例
            self.scale_factor_fill = st.sidebar.slider("背景填充轮廓检测最小面积比例 ", min_value=0.1, max_value=0.8, value=0.1, step=0.05)
        st.sidebar.caption("💡 提示: 梯形校正用于修正图像的透视畸变，适用于拍摄角度不正的图像。目前仅适用于EL图像检测。")

        # 添加图像增强选项
        self.image_enhancement_method = st.sidebar.radio(
            "选择图像增强方法",
            options=["不处理", "CLAHE", "Histogram Equalization"],
            index=0  # 默认选择不处理
        )
        st.sidebar.caption("💡 提示: 图像增强可以改善图像的对比度和细节，使检测结果更加准确。")

        # 添加图像畸变校正选项
        self.undistortion_method = st.sidebar.radio(
            "选择相机畸变校正类型",
            options=["不去除", "相机参数计算", "手动调整参数"],
            index=0  # 默认选择第一个选项
        )
        st.sidebar.caption("💡 提示: 相机参数计算需要用户输入相机标定文件，手动调整参数需要保证输入图像包含较为明显的线条用于修正畸变。")

        if self.undistortion_method == "相机参数计算":
            calibration_file = st.sidebar.file_uploader(
                "上传相机标定文件 (JSON, 包含camera_matrix和dist_coeffs)", type=["json"]
            )
            calibration_input = st.sidebar.text_area(
                "或直接粘贴标定参数（JSON字符串或Python字典）", value="", height=150
            )
            calib_data = None
            if calibration_file is not None:
                try:
                    calib_data = json.load(calibration_file)
                    self.camera_matrix = np.array(calib_data["camera_matrix"])
                    self.dist_coeffs = np.array(calib_data["dist_coeffs"])
                    self.calibration_file = calibration_file.name
                    st.sidebar.success("相机标定参数加载成功！")
                except Exception as e:
                    st.sidebar.error(f"标定文件解析失败: {e}")
            elif calibration_input.strip():
                try:
                    # 尝试先用json解析，否则用eval（仅限受信环境）
                    try:
                        calib_data = json.loads(calibration_input)
                    except Exception:
                        calib_data = eval(calibration_input, {"__builtins__": {}})
                    self.calibration_file = "sidebar_input"
                except Exception as e:
                    st.sidebar.error(f"标定参数解析失败: {e}")
            if calib_data is not None:
                try:
                    self.camera_matrix = np.array(calib_data["camera_matrix"])
                    self.dist_coeffs = np.array(calib_data["dist_coeffs"])
                    st.sidebar.success("相机标定参数加载成功！")
                except Exception as e:
                    st.sidebar.error(f"标定参数内容有误: {e}")
                    self.camera_matrix = None
                    self.dist_coeffs = None
                    self.calibration_file = None
            else:
                self.camera_matrix = None
                self.dist_coeffs = None
                self.calibration_file = None
        elif self.undistortion_method == "手动调整参数":
            # Add slider for distortion coefficient
            self.image_k1 = st.sidebar.slider("调整畸变系数 (k1)", min_value=-0.5, max_value=0.5, value=0.0, step=0.01)
            st.sidebar.caption("💡 提示: 畸变系数用于描述镜头的径向畸变。畸变系数大于0：桶形畸变，图像边缘向外扩展；畸变系数小于0：枕形畸变，图像边缘向内收缩。")

        # Apply distortion adjustment using the slider value
        if self.uploaded_file:
            if isinstance(self.uploaded_file, list):  # Handle multiple file uploads
                total_files = len(self.uploaded_file)
                
                # 初始化侧边栏图片预览索引
                if 'sidebar_preview_index' not in st.session_state:
                    st.session_state['sidebar_preview_index'] = 0
                
                # 确保索引在有效范围内
                current_preview_index = min(st.session_state['sidebar_preview_index'], total_files - 1)
                st.session_state['sidebar_preview_index'] = current_preview_index
                
                # 侧边栏图片预览控制
                st.sidebar.subheader(MAIN_HEADERS["image_preprocessing_preview"])
                
                # 图片切换控件
                preview_col1, preview_col2, preview_col3 = st.sidebar.columns([1, 2, 1])
                
                with preview_col1:
                    if st.button("⬅️", key="sidebar_prev", disabled=(current_preview_index <= 0)):
                        st.session_state['sidebar_preview_index'] = max(0, current_preview_index - 1)
                        st.rerun()
                
                with preview_col2:
                    st.write(f"**{current_preview_index + 1} / {total_files}**")
                
                with preview_col3:
                    if st.button("➡️", key="sidebar_next", disabled=(current_preview_index >= total_files - 1)):
                        st.session_state['sidebar_preview_index'] = min(total_files - 1, current_preview_index + 1)
                        st.rerun()
                
                # 进度条显示
                progress_value = (current_preview_index + 1) / total_files
                st.sidebar.progress(progress_value)
                
                # 图片选择滑块
                new_preview_index = st.sidebar.slider(
                    "选择预览图片", 
                    min_value=0, 
                    max_value=total_files - 1, 
                    value=current_preview_index,
                    key="sidebar_image_slider"
                )
                
                # 如果滑块值改变，更新索引
                if new_preview_index != current_preview_index:
                    st.session_state['sidebar_preview_index'] = new_preview_index
                    st.rerun()
                
                # 显示当前选中的图片
                uploaded_file = self.uploaded_file[current_preview_index]
                
                try:
                    # 处理当前选中的图片
                    if hasattr(uploaded_file, 'read'):
                        uploaded_file.seek(0)
                        source_img = uploaded_file.read()
                        file_name = uploaded_file.name
                    else:
                        # 处理 LocalFileObj
                        with open(uploaded_file.name, 'rb') as f:
                            source_img = f.read()
                        file_name = os.path.basename(uploaded_file.name)
                    
                    file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                    image_ini = cv2.imdecode(file_bytes, 1)
                    
                    if image_ini is None:
                        st.sidebar.error(f"❌ 无法解码图片: {file_name}")
                    else:
                        # 应用各种图像处理
                        if self.enable_pseudo_color and is_black_and_white(image_ini):
                            converted_image = convert_to_pseudo_colorizer(image_ini, contrast=self.image_contrast, brightness=self.image_brightness)
                        else:
                            converted_image = image_ini.copy()

                        if self.enable_rotate_correction:
                            corrected_image = rotate_image(converted_image, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)
                        else:
                            corrected_image = converted_image.copy()

                        if self.enable_auto_keystone_correction:
                            corrected_image = auto_keystone_correction(corrected_image, scale_factor=self.scale_factor_keystone)
                        else:
                            corrected_image = corrected_image.copy()

                        if self.enable_background_fill:
                            corrected_image = fill_largest_polygon_white(corrected_image, scale_factor=self.scale_factor_fill)
                        else:
                            corrected_image = corrected_image.copy()

                        if self.image_enhancement_method == "CLAHE":
                            corrected_image = enhance_texture(corrected_image, method="clahe")
                        elif self.image_enhancement_method == "Histogram Equalization":
                            corrected_image = enhance_texture(corrected_image, method="histogram_equalization")
                        else:
                            corrected_image = corrected_image.copy()

                        if self.undistortion_method == "相机参数计算" and self.camera_matrix is not None and self.dist_coeffs is not None:
                            distorted_image = camera_undistortion(corrected_image, self.camera_matrix, self.dist_coeffs)
                        elif self.undistortion_method == "手动调整参数":
                            distorted_image = auto_undistort_image(corrected_image, self.image_k1)
                        else:
                            distorted_image = corrected_image.copy()

                        # 显示当前图片的处理前后对比
                        st.sidebar.image([image_ini, distorted_image], caption=[f"原始图像: {file_name}", f"调整后图像: {file_name}"], channels="BGR")
                        
                        # 显示图片信息
                        st.sidebar.caption(f"📄 文件名: {file_name}")
                        st.sidebar.caption(f"📐 尺寸: {image_ini.shape[1]} × {image_ini.shape[0]}")
                        
                except Exception as e:
                    st.sidebar.error(f"❌ 处理图片时出错: {str(e)}")
                    
            else:  # Handle single file upload
                source_img = self.uploaded_file.read()
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)
                
                if self.enable_pseudo_color and is_black_and_white(image_ini):
                    converted_image = convert_to_pseudo_colorizer(image_ini, contrast=self.image_contrast, brightness=self.image_brightness)
                else:
                    converted_image = image_ini.copy()

                if self.enable_rotate_correction:
                    corrected_image = rotate_image(converted_image, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)
                else:
                    corrected_image = converted_image.copy()

                if self.enable_auto_keystone_correction:
                    corrected_image = auto_keystone_correction(corrected_image, scale_factor=self.scale_factor_keystone)
                else:
                    corrected_image = corrected_image.copy()

                if self.enable_background_fill:
                    corrected_image = fill_largest_polygon_white(corrected_image, scale_factor=self.scale_factor_fill)
                else:
                    corrected_image = corrected_image.copy()

                if self.image_enhancement_method == "CLAHE":
                    corrected_image = enhance_texture(corrected_image, method="clahe")
                elif self.image_enhancement_method == "Histogram Equalization":
                    corrected_image = enhance_texture(corrected_image, method="histogram_equalization")
                else:
                    corrected_image = corrected_image.copy()

                if self.undistortion_method == "相机参数计算" and self.camera_matrix is not None and self.dist_coeffs is not None:
                    distorted_image = camera_undistortion(corrected_image, self.camera_matrix, self.dist_coeffs)
                elif self.undistortion_method == "手动调整参数":
                    distorted_image = auto_undistort_image(corrected_image, self.image_k1)
                else:
                    distorted_image = corrected_image.copy()

                # Display original and distorted images
                st.sidebar.image([image_ini, distorted_image], caption=[f"原始图像: {self.uploaded_file.name}", f"调整后的图像: {self.uploaded_file.name}"], channels="BGR")
        else:
            st.sidebar.warning(SIDEBAR_HINTS["upload_image_to_adjust_distortion"])

        st.sidebar.header(SIDEBAR_HEADERS["output_file_path"])
        self.output_path = st.sidebar.text_input(SIDEBAR_LABELS["output_file_path"], value=abs_path("../output", path_type="current"), placeholder="例如：../output 或 D:/videos")

        if self.input_source in ["摄像头", "RTSP/RTMP流"]:
            st.sidebar.header(SIDEBAR_HEADERS["rtsp_output_settings"])
            self.enable_rtsp_output = st.sidebar.checkbox(SIDEBAR_LABELS["enable_rtsp_output"], value=False)        # RTSP/RTMP输出地址输入
        if self.enable_rtsp_output:
            self.rtsp_output_url = st.sidebar.text_input(SIDEBAR_LABELS["rtsp_output_url"], placeholder="例如：rtmp://<ip>:<port>/live/stream 或 rtsp://<ip>:<port>/path")
            st.sidebar.write(SIDEBAR_HINTS["rtsp_output_hint"])

        # 🔧 调用调试函数
        self.debug_detection_settings()

    def debug_detection_settings(self):
        """
        调试检测设置，显示当前配置信息
        """
        if self.from_streamlit:
            with st.sidebar.expander(MAIN_LABELS["debug_messages"], expanded=False):
                st.subheader(MAIN_HEADERS["current_config"])
                st.write(f"- 模型类型: {getattr(self, 'model_type', 'None')}")
                st.write(f"- 图像类型: {getattr(self, 'image_type', 'None')}")
                st.write(f"- 矩形框输出: {getattr(self, 'rectangle_bounding_output', 'None')}")
                st.write(f"- 置信度阈值: {getattr(self, 'conf_threshold', 'None')}")
                st.write(f"- IOU阈值: {getattr(self, 'iou_threshold', 'None')}")
                
                st.write(MAIN_HEADERS["class_settings"])
                st.write(f"- 可用类别(中文): {getattr(self, 'available_classes', [])}")
                st.write(f"- 选择的类别(英文): {getattr(self, 'selected_classes', [])}")
                
                if hasattr(self, 'model') and hasattr(self.model, 'names'):
                    # 处理不同类型的 model.names
                    if isinstance(self.model.names, dict):
                        model_classes = list(self.model.names.values())
                    elif isinstance(self.model.names, list):
                        model_classes = self.model.names
                    else:
                        model_classes = str(self.model.names)
                    st.write(f"- 模型类别: {model_classes}")
                    
                if hasattr(self, 'cls_name'):
                    st.write(f"- 类别映射: {self.cls_name}")
                
                # 显示实时检测信息
                if hasattr(self, '_debug_detected_classes'):
                    st.write(MAIN_HEADERS["real_time_detection"])
                    st.write(f"- 当前检测到的类别: {getattr(self, '_debug_detected_classes', [])}")
                    st.write(f"- 类别匹配状态: {getattr(self, '_debug_class_matches', {})}")
                    
                st.write(MAIN_HEADERS["color_settings"])
                st.write(f"- 颜色列表长度: {len(getattr(self, 'colors', []))}")
                if hasattr(self, 'colors') and len(self.colors) > 0:
                    st.write(f"- 前3个颜色: {self.colors[:3]}")

    def debug_display_state(self):
        """
        调试显示状态，输出当前图像和检测结果的状态信息
        """
        if self.from_streamlit:
            with st.expander(MAIN_LABELS["display_status_debug"], expanded=False):
                st.subheader(MAIN_HEADERS["session_state_data"])
                st.write(f"- saved_images_ini 数量: {len(st.session_state.get('saved_images_ini', []))}")
                st.write(f"- saved_images 数量: {len(st.session_state.get('saved_images', []))}")
                st.write(f"- saved_names 数量: {len(st.session_state.get('saved_names', []))}")
                st.write(f"- 当前图片索引: {st.session_state.get('image_play_index', 'None')}")

                st.subheader(MAIN_HEADERS["logtable_data"])
                if hasattr(self, 'logTable'):
                    st.write(f"- logTable.saved_images_ini 数量: {len(getattr(self.logTable, 'saved_images_ini', []))}")
                    st.write(f"- logTable.saved_images 数量: {len(getattr(self.logTable, 'saved_images', []))}")
                    st.write(f"- logTable.saved_names 数量: {len(getattr(self.logTable, 'saved_names', []))}")
                else:
                    st.write("- logTable: 未初始化")

                st.subheader(MAIN_HEADERS["display_mode"])
                st.write(f"- 显示模式: {getattr(self, 'display_mode', 'None')}")
                st.write(f"- 选择的目标: {st.session_state.get('selectbox_target', 'None')}")

    # 🚀 性能优化方法
    def manage_cache_size(self, cache_dict):
        """管理缓存大小，避免内存泄漏"""
        if len(cache_dict) > self.max_cache_size:
            # 删除最旧的缓存条目
            oldest_key = next(iter(cache_dict))
            del cache_dict[oldest_key]

    def get_image_hash(self, image_data):
        """生成图像数据的哈希值用作缓存键"""
        if isinstance(image_data, bytes):
            return hashlib.md5(image_data).hexdigest()
        elif hasattr(image_data, 'read'):
            # 对于文件对象
            current_pos = image_data.tell()
            image_data.seek(0)
            hash_val = hashlib.md5(image_data.read()).hexdigest()
            image_data.seek(current_pos)
            return hash_val
        return None

    def cached_image_decode(self, image_data):
        """缓存图像解码操作"""
        cache_key = self.get_image_hash(image_data)
        if cache_key and cache_key in self.image_cache:
            return self.image_cache[cache_key].copy()
        
        # 解码图像
        if isinstance(image_data, bytes):
            file_bytes = np.asarray(bytearray(image_data), dtype=np.uint8)
        else:
            file_bytes = np.asarray(bytearray(image_data.read()), dtype=np.uint8)
        
        image = cv2.imdecode(file_bytes, 1)
        
        # 缓存结果
        if cache_key:
            self.manage_cache_size(self.image_cache)
            self.image_cache[cache_key] = image.copy()
        
        return image

    def optimized_image_resize(self, image, target_width=None, target_height=None):
        """优化的图像调整大小"""
        if target_width is None:
            target_width = self.display_width
        if target_height is None:
            target_height = self.display_height
            
        # 如果图像已经是目标尺寸，直接返回
        if image.shape[1] == target_width and image.shape[0] == target_height:
            return image
        
        return cv2.resize(image, (target_width, target_height))

    def batch_process_images(self, uploaded_files):
        """批量处理图像（异步）"""
        def process_single_image(uploaded_file):
            try:
                # 读取图片数据
                if hasattr(uploaded_file, 'read'):
                    uploaded_file.seek(0)
                    source_img = uploaded_file.read()
                    file_name = uploaded_file.name
                else:
                    # 处理 LocalFileObj
                    with open(uploaded_file.name, 'rb') as f:
                        source_img = f.read()
                    file_name = os.path.basename(uploaded_file.name)
                
                # 解码图片
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)
                
                if image_ini is None:
                    return {
                        'name': file_name,
                        'error': '无法解码图片',
                        'status': 'error'
                    }
                
                # 应用图像处理
                processed_image = self.apply_image_processing(image_ini)
                
                # 进行检测
                framecopy = processed_image.copy()
                image, detInfo, select_info = self.frame_process(framecopy, file_name)
                
                # 保存结果
                save_chinese_image(self.output_path + '/image/' + file_name, image)
                
                return {
                    'name': file_name,
                    'original': image,
                    'processed': processed_image,
                    'status': 'success'
                }
            except Exception as e:
                return {
                    'name': file_name if hasattr(uploaded_file, 'name') else 'unknown',
                    'error': str(e),
                    'status': 'error'
                }
        
        # 使用线程池进行并行处理
        if len(uploaded_files) > 1:
            futures = [self.executor.submit(process_single_image, f) for f in uploaded_files]
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                except Exception as e:
                    results.append({'error': str(e), 'status': 'timeout'})
            return results
        else:
            # 单个文件直接处理
            return [process_single_image(uploaded_files[0])]

    def apply_image_processing(self, image):
        """应用图像处理流水线"""
        processed = image.copy()
        
        # 去畸变
        if hasattr(self, 'undistortion_method'):
            if self.undistortion_method == "相机参数计算" and hasattr(self, 'camera_matrix'):
                if self.camera_matrix is not None and self.dist_coeffs is not None:
                    processed = camera_undistortion(processed, self.camera_matrix, self.dist_coeffs)
            elif self.undistortion_method == "手动调整参数" and hasattr(self, 'image_k1'):
                processed = auto_undistort_image(processed, self.image_k1)

        # 梯形校正
        if hasattr(self, 'enable_rotate_correction') and self.enable_rotate_correction:
            processed = rotate_image(
                processed, 
                angle_x=getattr(self, 'rot_angle_x', 0),
                angle_y=getattr(self, 'rot_angle_y', 0), 
                zoom_factor=getattr(self, 'keystone_scale', 1.0)
            )

        if hasattr(self, 'enable_auto_keystone_correction') and self.enable_auto_keystone_correction:
            processed = auto_keystone_correction(processed, scale_factor=getattr(self, 'scale_factor_keystone', 1.0))

        if hasattr(self, 'enable_background_fill') and self.enable_background_fill:
            processed = fill_largest_polygon_white(processed, scale_factor=getattr(self, 'scale_factor_fill', 1.0))

        # 图像增强
        if hasattr(self, 'image_enhancement_method'):
            if self.image_enhancement_method == "CLAHE":
                processed = enhance_texture(processed, method="clahe")
            elif self.image_enhancement_method == "Histogram Equalization":
                processed = enhance_texture(processed, method="histogram_equalization")

        # 伪彩色处理
        if hasattr(self, 'enable_pseudo_color') and self.enable_pseudo_color:
            if is_black_and_white(processed):
                processed = convert_to_pseudo_colorizer(
                    processed,
                    contrast=getattr(self, 'image_contrast', 1.0),
                    brightness=getattr(self, 'image_brightness', 0)
                )

        return processed

    def toggle_comboBox(self, frame_id):
        """
        处理并显示指定帧的检测结果。

        Args:
            frame_id (int): 指定要显示检测结果的帧ID。

        根据用户选择的目标过滤选项，显示该帧的检测结果和图像。
        """
        # 优先使用session state中的数据，确保数据一致性
        saved_images_ini = st.session_state.get('saved_images_ini', [])
        saved_images = st.session_state.get('saved_images', [])
        saved_results = getattr(self.logTable, 'saved_results', [])
        saved_names = st.session_state.get('saved_names', [])
        
        # 如果session state为空但logTable有数据，同步数据
        if not saved_images_ini and hasattr(self.logTable, 'saved_images_ini') and self.logTable.saved_images_ini:
            saved_images_ini = self.logTable.saved_images_ini
            saved_images = getattr(self.logTable, 'saved_images', [])
            saved_names = getattr(self.logTable, 'saved_names', [])
            # 同步到session state
            st.session_state['saved_images_ini'] = saved_images_ini
            st.session_state['saved_images'] = saved_images
            st.session_state['saved_names'] = saved_names
        
        if frame_id == -1:  # 显示所有目标
            if not saved_images_ini:
                st.warning(STATUS_MESSAGES["no_detection_results"])
                if hasattr(self, 'image_placeholder'):
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
                if hasattr(self, 'table_placeholder'):
                    self.table_placeholder.table(pd.DataFrame(columns=["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)"]))
                return
            frame_id = 0  # 默认显示第一帧

        if frame_id >= len(saved_images_ini) or frame_id >= len(saved_results):
            st.warning(STATUS_MESSAGES["frame_id_out_of_range_warning"].format(frame_id=frame_id, total=len(saved_images_ini)))
            return

        # 获取当前选中的目标过滤选项
        selected_target = st.session_state.get('selectbox_target', SYSTEM_CONFIG["target_all"])

        # 获取原始帧
        frame = saved_images_ini[frame_id]  # 获取指定帧的初始图像

        # 缓存图像调整大小的结果
        cache_key = f"frame_{frame_id}_{self.display_width}_{self.display_height}_{selected_target}"
        if cache_key in self.image_cache:
            image = self.image_cache[cache_key]
        else:
            # 创建图像副本并处理检测框
            image = frame.copy()
            
            # 绘制检测框
            detection_results = self.logTable.saved_results[frame_id]
            if detection_results:
                cnt = 0
                for detInfo in detection_results:
                    if isinstance(detInfo, list) and len(detInfo) == 6:
                        name, chinese_name, bbox, conf, use_time, cls_id = detInfo

                        # 如果选择了目标过滤，跳过不匹配的目标
                        if selected_target != SYSTEM_CONFIG["target_all"] and selected_target != chinese_name:
                            continue

                        # 确保 cls_id 在范围内
                        if cls_id < len(self.colors):
                            color = self.colors[cls_id]
                        else:
                            color = (255, 0, 0)  # 默认红色

                        # 确保矩形框绘制参数正确
                        info = {
                            'class_name': name,
                            'bbox': bbox,
                            'score': conf,
                            'class_id': cls_id,
                            'mask': None
                        }
                        # 使用更明显的参数来绘制检测框
                        image, _ = draw_detections(
                            image, info, 
                            color=color, 
                            alpha=0.3,  # 增加透明度使框更明显
                            line_number=cnt,
                            rectangle_bbox=getattr(self, 'rectangle_bounding_output', True)
                        )
                        cnt += 1
            
            # 缓存处理后的图像
            self.manage_cache_size(self.image_cache)
            self.image_cache[cache_key] = image.copy()

        # 现在不需要重复绘制检测框，因为已经在缓存逻辑中处理了

        # 调整图像大小
        if hasattr(self, 'optimized_image_resize'):
            resized_image = self.optimized_image_resize(image, self.display_width, self.display_height)
            resized_frame = self.optimized_image_resize(frame, self.display_width, self.display_height)
        else:
            resized_image = cv2.resize(image, (self.display_width, self.display_height))
            resized_frame = cv2.resize(frame, (self.display_width, self.display_height))

        # 更新表格数据
        detection_results = saved_results[frame_id] if frame_id < len(saved_results) else []
        
        if detection_results:
            # 使用列表推导式提高性能
            filtered_results = [
                detInfo for detInfo in detection_results
                if isinstance(detInfo, list) and len(detInfo) == 6 and
                (selected_target == SYSTEM_CONFIG["target_all"] or selected_target == detInfo[1])
            ]
            
            if filtered_results and hasattr(self, 'table_placeholder'):
                disp_res = ResultLogger()
                for detInfo in filtered_results:
                    name, chinese_name, bbox, conf, use_time, cls_id = detInfo
                    disp_res.concat_results(name, chinese_name, bbox, str(round(conf, 2)), str(use_time))
                self.table_placeholder.table(disp_res.results_df)
            else:
                if hasattr(self, 'table_placeholder'):
                    self.table_placeholder.table(pd.DataFrame(columns=["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)"]))
        else:
            if hasattr(self, 'table_placeholder'):
                self.table_placeholder.table(pd.DataFrame(columns=["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)"]))

        # 获取图像名称
        img_name = saved_names[frame_id] if frame_id < len(saved_names) else f"Frame_{frame_id}"

        # 根据显示模式显示处理后的图像或原始图像
        if hasattr(self, 'display_mode') and hasattr(self, 'image_placeholder'):
            if self.display_mode == "叠加显示":
                self.image_placeholder.image(resized_image, channels="BGR", caption="识别画面: " + img_name)
            else:  # "对比显示"
                self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面: " + img_name)
                if hasattr(self, 'image_placeholder_res'):
                    self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面: " + img_name)

    def frame_process(self, image, file_name, video_time=None, is_api=False):
        """
        处理并预测单个图像帧的内容。

        Args:
            image (numpy.ndarray): 输入的图像。
            file_name (str): 处理的文件名。
            video_time (str, optional): 视频时间戳，默认为 None。
            is_api (bool, optional): 是否使用API功能，默认为 False。

        Returns:
            tuple: 处理后的图像，检测信息，选择信息列表。

        对输入图像进行预处理，使用模型进行预测，并处理预测结果。
        """
        # image = cv2.resize(image, (640, 640))  # 调整图像大小以适应模型
        pre_img = self.model.preprocess(image)  # 对图像进行预处理

        # 更新模型参数
        params = {'conf': self.conf_threshold, 'iou': self.iou_threshold}
        self.model.set_param(params)

        t1 = time.time()
        pred = self.model.predict(pre_img)  # 使用模型进行预测

        t2 = time.time()
        use_time = t2 - t1  # 计算单张图片推理时间
        self.detection_time = use_time  # 更新检测时间

        det = pred[0]  # 获取预测结果

        # 初始化检测信息和选择信息列表
        detInfo = []
        select_info = ["全部目标"]

        # 如果有有效的检测结果
        if det is not None and len(det):
            det_info = self.model.postprocess(pred)  # 后处理预测结果
            if len(det_info):
                disp_res = ResultLogger()
                res = None
                cnt = 0

                # 初始化调试信息存储
                self._debug_detected_classes = []
                self._debug_class_matches = {}
                
                # 遍历检测到的对象
                for idx, info in enumerate(det_info):
                    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']

                    # 收集调试信息（不直接显示）
                    if idx == 0:  # 只在第一个检测对象时收集，避免重复
                        self._debug_detected_classes = [info['class_name'] for info in det_info]
                        for det_info_item in det_info:
                            det_name = det_info_item['class_name']
                            self._debug_class_matches[det_name] = det_name in self.selected_classes

                    # Ensure cls_id is within bounds
                    if cls_id >= len(self.colors):
                        st.warning(STATUS_MESSAGES["index_out_of_range_warning"].format(cls_id=cls_id))
                        color = (255, 0, 0)  # 默认红色
                    else:
                        color = self.colors[cls_id]

                    # 🔧 确保类别匹配逻辑正确
                    if name in self.selected_classes:
                        # 绘制检测框、标签和面积信息
                        if not is_api:
                            image, aim_frame_area = draw_detections(image, info, color=color, alpha=0.5, line_number=cnt, rectangle_bbox=self.rectangle_bounding_output)
                        else:
                            image, aim_frame_area = draw_detections(image, info, alpha=0.5, line_number=cnt, is_api=True, rectangle_bbox=self.rectangle_bounding_output)

                        # 获取中文名
                        chinese_name = self.cls_name.get(name, "未知类别")

                        res = disp_res.concat_results(name, chinese_name, bbox, str(int(aim_frame_area)),
                                                    video_time if video_time is not None else str(round(use_time, 2)))

                        # 添加日志条目
                        self.logTable.add_log_entry(file_name, name, chinese_name, bbox, int(aim_frame_area), video_time if video_time is not None else str(round(use_time, 2)))
                        # 记录检测信息
                        detInfo.append([name, chinese_name, bbox, int(aim_frame_area), video_time if video_time is not None else str(round(use_time, 2)), cls_id])

                        # 添加到选择信息列表，避免重复
                        if chinese_name not in select_info:
                            select_info.append(chinese_name)
                        cnt += 1

                # 在表格中显示检测结果
                if not is_api:
                    self.table_placeholder.table(res)

        if not select_info:
            select_info = ["全部目标"]
        st.session_state['select_info'] = select_info
        return image, detInfo, select_info

    def frame_table_process(self, frame, caption):
        """
        处理并显示视频帧的检测结果。

        Args:
            frame (numpy.ndarray): 输入的视频帧。
            caption (str): 显示的标题或说明。
        """
        # 显示画面并更新结果
       
        self.image_placeholder.image(frame, channels="BGR", caption=caption)

        # 更新检测结果
        detection_result = "None"
        detection_location = "[0, 0, 0, 0]"
        detection_confidence = str(random.random())
        detection_time = "0.00s"

        # 使用 display_detection_results 函数显示结果
        res = concat_results(detection_result, detection_location, detection_confidence, detection_time)
        self.table_placeholder.table(res)
        # 添加适当的延迟
        cv2.waitKey(1)

    def setupMainWindow(self):
        """
        运行检测系统。
        """

        # 使用自定义 CSS 样式调整列的宽度
        st.markdown(
            """
            <style>
                [data-testid="column"]:nth-of-type(1) {
                    min-width: 800px !important; /* 设置第一列的最小宽度 */
                }
                [data-testid="column"]:nth-of-type(2) {
                    min-width: 300px !important; /* 设置第二列的最小宽度 */
                }
                [data-testid="column"]:nth-of-type(3) {
                    min-width: 600px !important; /* 设置第三列的最小宽度 */
                }
            </style>
            """,
            unsafe_allow_html=True
        )

        # st.title(self.title) # 显示系统标题
        st.write("--------")
        st.write("本系统可以检测光伏面板可见光故障、红外热故障、EL隐裂故障以及其他异物入侵等问题。")
        st.write("--------")
        # 插入一条分割线

        # 创建列布局，将表格移到最右侧
        col1, col2 = st.columns([1, 1])

        # 在第一列设置显示模式的选择
        with col1:
            st.subheader(MAIN_HEADERS["video_image_detection_system"])
            self.display_mode = st.radio(MAIN_LABELS["display_mode_selection"], ["叠加显示", "对比显示"])
            self.image_placeholder = st.empty()
            self.image_placeholder_res = st.empty()
            # 根据显示模式创建用于显示视频画面的空容器，优化默认图像显示逻辑，避免覆盖检测结果
            if self.display_mode == "叠加显示":
                # 只在没有任何保存图像且没有session state中的图像时显示默认图像
                if (not hasattr(self.logTable, 'saved_images_ini') or 
                    not self.logTable.saved_images_ini) and \
                   (not st.session_state.get('saved_images_ini')):
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
            else:
                # "双画面显示"
                if (not hasattr(self.logTable, 'saved_images_ini') or 
                    not self.logTable.saved_images_ini) and \
                   (not st.session_state.get('saved_images_ini')):
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
                    self.image_placeholder_res.image(load_default_image(), caption="识别画面")
            # 显示用的进度条
            self.progress_bar = st.progress(0)

        # 创建一个空的结果表格
        res = concat_results("None", "[0, 0, 0, 0]", "0.00", "0.00s")

        # 在最右侧列设置识别结果表格的显示
        with col2:
            st.subheader(MAIN_HEADERS["current_image_results"])
            self.table_placeholder = st.empty()  # 调整到最右侧显示
            self.table_placeholder.table(res)

            self.selectbox_placeholder = st.empty()

            # 初始化目标过滤选项 - 根据当前图片动态获取检测目标
            idx = st.session_state.get('image_play_index', 0)
            
            # 获取当前图片的检测目标（优先从session_state获取，然后从logTable获取）
            saved_targets_info = st.session_state.get('saved_targets_info', [])
            if not saved_targets_info and hasattr(self.logTable, 'saved_targets_info'):
                saved_targets_info = self.logTable.saved_targets_info
                # 同步到session_state
                st.session_state['saved_targets_info'] = saved_targets_info
            
            if saved_targets_info and idx < len(saved_targets_info):
                detected_targets = saved_targets_info[idx]
            else:
                detected_targets = st.session_state.get("select_info", ["全部目标"])
            
            # selectbox动态key，确保当目标列表变化时selectbox会刷新
            selectbox_key = f"selectbox_target_{idx}_{hash(tuple(detected_targets))}"
            
            # 确保当前选中的目标在新的目标列表中，如果不在则重置为"全部目标"
            current_selected = st.session_state.get('selectbox_target', "全部目标")
            if current_selected not in detected_targets:
                current_selected = "全部目标"
                st.session_state['selectbox_target'] = current_selected
            
            # 获取当前选中目标在列表中的索引
            try:
                current_index = detected_targets.index(current_selected)
            except ValueError:
                current_index = 0
                current_selected = detected_targets[0] if detected_targets else "全部目标"
                st.session_state['selectbox_target'] = current_selected
            
            selectbox_target = self.selectbox_placeholder.selectbox(
                MAIN_LABELS["target_filter"], 
                detected_targets, 
                key=selectbox_key, 
                index=current_index
            )
            
            # 只在选项变化时同步并刷新显示
            if 'last_target' not in st.session_state or st.session_state['last_target'] != selectbox_target:
                self.selectbox_target = selectbox_target
                st.session_state['selectbox_target'] = selectbox_target
                st.session_state['last_target'] = selectbox_target
                self.toggle_comboBox(idx)

            # 创建一个导出结果的按钮
            st.write("---------------------")
            if st.button(BUTTON_TEXTS["export_results"]):
                current_time = datetime.now().strftime("%Y年%m月%d日_%H时%M分")
                
                # 使用新的命名配置生成文件名
                base_filename = generate_filename(
                    "report",
                    image_type=self.image_type,
                    task_type=self.model_type,
                    timestamp=current_time
                )
                self.saved_log_data = os.path.join(self.csv_output_path, base_filename)

                if self.export_format == "CSV":
                    self.saved_log_data += ".csv"
                    self.logTable.save_to_csv(self.saved_log_data)
                    st.success(STATUS_MESSAGES["export_success"].format(
                                                file_type="CSV数据表", 
                                                filename=os.path.basename(self.saved_log_data)))
                elif self.export_format == "Excel":
                    self.saved_log_data += ".xlsx"
                    self.logTable.save_to_excel(self.saved_log_data)
                    st.success(STATUS_MESSAGES["export_success"].format(
                                                file_type="Excel电子表格", 
                                                filename=os.path.basename(self.saved_log_data)))
                elif self.export_format == "JSON":
                    self.saved_log_data += ".json"
                    self.logTable.save_to_json(self.saved_log_data)
                    st.success(STATUS_MESSAGES["export_success"].format( 
                                                file_type="JSON数据文件", 
                                                filename=os.path.basename(self.saved_log_data)))
                elif self.export_format == "Word":
                    self.saved_log_data += ".docx"
                    # 构建检测参数字典
                    detection_params = {
                        'model_type': self.model_type,
                        'image_type': self.image_type,
                        'conf_threshold': self.conf_threshold,
                        'iou_threshold': self.iou_threshold,
                        'selected_classes': getattr(self, 'selected_classes', []),
                        'cls_name': getattr(self, 'cls_name', {})
                    }
                    self.logTable.save_to_word(self.saved_log_data, detection_params)
                    st.success(STATUS_MESSAGES["export_success"].format( 
                                                file_type="Word检测报告", 
                                                filename=os.path.basename(self.saved_log_data)))

                self.logTable.clear_data()
            st.subheader(MAIN_HEADERS["history_log"])
            # 显示所有结果记录的空白表格
            self.log_table_placeholder = st.empty()
            self.logTable.update_table(self.log_table_placeholder)

        # 在第五列设置一个空的停止按钮占位符

        with col1:
            st.write("")
            run_button = st.button(BUTTON_TEXTS["start_detection"])
            self.close_placeholder = st.empty()

        # 将切换按钮移到独立区域，并简化显示逻辑
        st.markdown("---")
        st.subheader(MAIN_HEADERS["image_browser_control"])
        
        # 检查是否有检测结果（优先检查session state，然后检查logTable）
        saved_images_ini = st.session_state.get('saved_images_ini', [])
        if not saved_images_ini and hasattr(self.logTable, 'saved_images_ini'):
            saved_images_ini = self.logTable.saved_images_ini
            # 同步到session state
            st.session_state['saved_images_ini'] = saved_images_ini
            st.session_state['saved_images'] = getattr(self.logTable, 'saved_images', [])
            st.session_state['saved_names'] = getattr(self.logTable, 'saved_names', [])
        
        if len(saved_images_ini) > 0:
            total_imgs = len(saved_images_ini)
            st.info(STATUS_MESSAGES["total_images_info"].format(count=total_imgs))
            
            # 初始化或验证图片索引
            if 'image_play_index' not in st.session_state:
                st.session_state['image_play_index'] = 0
            elif st.session_state['image_play_index'] >= total_imgs:
                st.session_state['image_play_index'] = total_imgs - 1
                
            current_index = st.session_state['image_play_index']
            
            # 创建三列布局：[上一张] [当前信息] [下一张]
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            
            with col_prev:
                if st.button(BUTTON_TEXTS["previous_image"], key="prev_btn", disabled=(current_index <= 0)):
                    st.session_state['image_play_index'] = max(0, current_index - 1)
                    st.rerun()
            
            with col_info:
                st.write(STATUS_MESSAGES["image_index_info"].format(current=current_index + 1, total=total_imgs))
                # 显示当前图片名称
                if current_index < len(st.session_state.get('saved_names', [])):
                    img_name = st.session_state['saved_names'][current_index]
                    st.caption(STATUS_MESSAGES["filename_info"].format(filename=img_name))
            
            with col_next:
                if st.button(BUTTON_TEXTS["next_image"], key="next_btn", disabled=(current_index >= total_imgs - 1)):
                    st.session_state['image_play_index'] = min(total_imgs - 1, current_index + 1)
                    st.rerun()
            
            # 添加滑块控制
            new_index = st.slider(
                MAIN_LABELS["image_slider_label"], 
                min_value=0, 
                max_value=total_imgs - 1, 
                value=current_index,
                key="image_slider"
            )
            
            # 如果滑块值改变，更新索引
            if new_index != current_index:
                st.session_state['image_play_index'] = new_index
                st.rerun()
            
            # 显示检测结果
            self.toggle_comboBox(st.session_state['image_play_index'])
            
        else:
            st.info(STATUS_MESSAGES["no_detection_results"])
            # 显示默认图像
            if hasattr(self, 'image_placeholder'):
                self.image_placeholder.image(load_default_image(), caption="原始画面")
                if self.display_mode == "对比显示" and hasattr(self, 'image_placeholder_res'):
                    self.image_placeholder_res.image(load_default_image(), caption="识别画面")

        st.subheader(MAIN_HEADERS["realtime_dashboard"])
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            self.frame_count_placeholder = st.empty()
        with col2:
            self.fps_placeholder = st.empty()
        with col3:
            self.target_count_placeholder = st.empty()
        with col4:
            self.detection_time_placeholder = st.empty()

        # 初始化默认值
        self.frame_count_placeholder.metric(STATUS_MESSAGES["current_frame_metric"], st.session_state['current_frame_count'])
        self.fps_placeholder.metric(STATUS_MESSAGES["current_fps_metric"], st.session_state['current_fps'])
        self.target_count_placeholder.metric(STATUS_MESSAGES["target_count_metric"], st.session_state['current_target_count'])
        self.detection_time_placeholder.metric(STATUS_MESSAGES["detection_time_metric"], st.session_state['current_detection_time'])

        # 🔧 添加调试信息
        self.debug_display_state()

        if run_button:
            self.process_camera_or_file()  # 运行摄像头或文件处理
            st.rerun()

    def process_camera_or_file(self):
        """
        根据输入源类型处理不同的输入（摄像头、文件、RTSP流等）
        """
        try:
            # 确保所有必需的属性都已初始化
            self._ensure_initialization()
            
            if self.input_source == "图片文件" or self.input_source == "图片文件夹":
                if self.uploaded_file:
                    self._process_image_input()
                else:
                    st.warning(STATUS_MESSAGES["upload_files_first"])
                    
            elif self.input_source == "视频文件" or self.input_source == "视频文件夹":
                if hasattr(self, 'uploaded_video') and self.uploaded_video:
                    self._process_video_input()
                else:
                    st.warning(STATUS_MESSAGES["upload_video_first"])
                    
            elif self.input_source == "摄像头":
                if self.selected_camera is not None:
                    camera_id = int(self.selected_camera.split(':')[0]) if ':' in str(self.selected_camera) else int(self.selected_camera)
                    self._process_camera_input(camera_id)
                else:
                    st.warning(STATUS_MESSAGES["select_camera_first"])

            elif self.input_source == "RTSP/RTMP流":
                if self.rtsp_input_url:
                    self._process_rtsp_input(self.rtsp_input_url)
                else:
                    st.warning(STATUS_MESSAGES["input_rtsp_first"])
                    
            else:
                st.error(STATUS_MESSAGES["unsupported_input_source"].format(source=self.input_source))

        except Exception as e:
            st.error(STATUS_MESSAGES["input_processing_error"].format(error=str(e)))

    def _ensure_initialization(self):
        """
        确保所有必需的属性都已正确初始化
        """
        # 确保 logTable 存在
        if not hasattr(self, 'logTable') or self.logTable is None:
            if hasattr(st, 'session_state') and 'logTable' in st.session_state:
                self.logTable = st.session_state['logTable']
            else:
                # 如果 saved_log_data 不存在，创建一个默认的
                if not hasattr(self, 'saved_log_data'):
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.saved_log_data = os.path.join(
                        getattr(self, 'csv_output_path', abs_path("../output/logs/", path_type="current")),
                        f"log_table_data_{current_time}.csv"
                    )
                
                self.logTable = LogTable(self.saved_log_data)
                if hasattr(st, 'session_state'):
                    st.session_state['logTable'] = self.logTable
        
        # 确保 progress_bar 存在
        if not hasattr(self, 'progress_bar') or self.progress_bar is None:
            self.progress_bar = st.progress(0)
        
        # 确保 close_placeholder 存在
        if not hasattr(self, 'close_placeholder') or self.close_placeholder is None:
            self.close_placeholder = st.empty()
        
        # 确保显示相关属性存在
        if not hasattr(self, 'display_width'):
            self.display_width = 640
        if not hasattr(self, 'display_height'):
            self.display_height = 480

    def _process_image_input(self):
        """
        处理图片输入
        """
        if not self.uploaded_file:
            st.warning(SIDEBAR_HINTS["upload_files_first"])
            return
            
        self.logTable.clear_frames()
        
        # 初始化进度显示
        progress_container = st.container()
        with progress_container:
            st.info(STATUS_MESSAGES["image_detection_start"])
            overall_progress = st.progress(0)
            status_text = st.empty()
            current_image_info = st.empty()

        if isinstance(self.uploaded_file, list):
            # 批量处理多张图片
            total_files = len(self.uploaded_file)
            status_text.write(STATUS_MESSAGES["processing_files"].format(count=total_files))
            
            # 计算预估时间
            estimated_time_per_image = 2.0  # 假设每张图片需要2秒
            estimated_total_time = total_files * estimated_time_per_image
            status_text.write(STATUS_MESSAGES["estimated_time"].format(time=estimated_total_time))
            
            start_time = time.time()
            successful_count = 0
            failed_count = 0
            
            for idx, uploaded_file in enumerate(self.uploaded_file):
                try:
                    # 更新当前处理信息
                    current_file_name = uploaded_file.name if hasattr(uploaded_file, 'name') else f"图片_{idx+1}"
                    current_image_info.info(STATUS_MESSAGES["processing_current"].format(filename=current_file_name, current=idx + 1, total=total_files))

                    # 读取图片数据
                    if hasattr(uploaded_file, 'read'):
                        uploaded_file.seek(0)
                        source_img = uploaded_file.read()
                        file_name = uploaded_file.name
                    else:
                        # 处理 LocalFileObj
                        with open(uploaded_file.name, 'rb') as f:
                            source_img = f.read()
                        file_name = os.path.basename(uploaded_file.name)
                    
                    # 解码图片
                    file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                    image_ini = cv2.imdecode(file_bytes, 1)
                    
                    if image_ini is None:
                        st.error(STATUS_MESSAGES["image_decode_error"].format(filename=file_name))
                        failed_count += 1
                        continue
                    
                    # 应用图像处理
                    processed_image = self.apply_image_processing(image_ini)
                    
                    # 进行检测
                    framecopy = processed_image.copy()
                    image, detInfo, select_info = self.frame_process(framecopy, file_name)
                    
                    # 保存结果
                    save_chinese_image(self.output_path + '/image/' + file_name, image)
                    
                    # 更新状态
                    st.session_state['current_frame_count'] = idx + 1
                    st.session_state['current_target_count'] = len(detInfo)
                    st.session_state['current_detection_time'] = self.detection_time
                    
                    # 更新显示
                    self.frame_count_placeholder.metric(MAIN_LABELS["current_frame"], idx + 1)
                    self.target_count_placeholder.metric(MAIN_LABELS["target_count"], len(detInfo))
                    self.detection_time_placeholder.metric(MAIN_LABELS["detection_time"], self.detection_time)

                    # 显示图片
                    resized_image = cv2.resize(image, (self.display_width, self.display_height))
                    resized_frame = cv2.resize(processed_image, (self.display_width, self.display_height))
                    
                    if self.display_mode == "叠加显示":
                        self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {file_name}")
                    else:
                        self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {file_name}")
                        if hasattr(self, 'image_placeholder_res'):
                            self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {file_name}")
                    
                    # 添加到日志表
                    self.logTable.add_frames(image, detInfo, processed_image, file_name)
                    
                    successful_count += 1
                    
                    # 更新进度条和状态
                    progress = (idx + 1) / total_files
                    overall_progress.progress(progress)
                    
                    # 计算剩余时间
                    elapsed_time = time.time() - start_time
                    if idx > 0:
                        avg_time_per_image = elapsed_time / (idx + 1)
                        remaining_images = total_files - (idx + 1)
                        remaining_time = remaining_images * avg_time_per_image
                        status_text.success(STATUS_MESSAGES["batch_processing_progress"].format(
                            current=idx + 1, 
                            total=total_files,
                            remaining_time=round(remaining_time, 2)
                        ))
                    
                    # 添加短暂延迟以显示进度
                    time.sleep(0.1)
                    
                except Exception as e:
                    st.error(STATUS_MESSAGES["image_processing_error"].format(filename=current_file_name, error=str(e)))
                    failed_count += 1
                    continue
            
            # 完成后的总结
            total_time = time.time() - start_time
            current_image_info.success(STATUS_MESSAGES["batch_processing_complete"])
            status_text.success(STATUS_MESSAGES["batch_processing_summary"].format(
                successful_count=successful_count, 
                failed_count=failed_count, 
                total_time=total_time
            ))
            overall_progress.progress(1.0)
            
            # 立即更新session state以确保UI同步
            st.session_state['saved_images_ini'] = self.logTable.saved_images_ini.copy()
            st.session_state['saved_images'] = self.logTable.saved_images.copy()
            st.session_state['saved_names'] = self.logTable.saved_names.copy()
            # 同步每张图片的目标信息
            if hasattr(self.logTable, 'saved_targets_info'):
                st.session_state['saved_targets_info'] = self.logTable.saved_targets_info.copy()
            
            # 确保索引重置为0以显示第一张图片
            st.session_state['image_play_index'] = 0
            
            # 更新历史日志显示
            if hasattr(self, 'log_table_placeholder'):
                self.logTable.update_table(self.log_table_placeholder)
            
            # 立即刷新页面，让selectbox自动更新
            st.rerun()
            
        else:
            # 单张图片处理
            try:
                # 显示处理状态
                progress_container = st.container()
                with progress_container:
                    st.info(STATUS_MESSAGES["single_image_processing_start"])
                    single_progress = st.progress(0)
                    status_info = st.empty()
                
                status_info.write(STATUS_MESSAGES["reading_image_file"])
                single_progress.progress(0.2)
                
                source_img = self.uploaded_file.read()
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)
                
                if image_ini is None:
                    st.error(STATUS_MESSAGES["image_decode_failed"])
                    return
                
                status_info.write(STATUS_MESSAGES["applying_image_processing"])
                single_progress.progress(0.4)
                
                # 应用图像处理
                processed_image = self.apply_image_processing(image_ini)
                
                status_info.write(STATUS_MESSAGES["ai_detection_running"])
                single_progress.progress(0.6)
                
                # 进行检测
                framecopy = processed_image.copy()
                image, detInfo, select_info = self.frame_process(framecopy, self.uploaded_file.name)
                
                status_info.write(STATUS_MESSAGES["saving_detection_results"])
                single_progress.progress(0.8)
                
                # 保存结果
                save_chinese_image(self.output_path + '/image/' + self.uploaded_file.name, image)
                
                # 更新状态
                st.session_state['current_frame_count'] = 1
                st.session_state['current_target_count'] = len(detInfo)
                st.session_state['current_detection_time'] = self.detection_time
                
                # 更新显示
                self.frame_count_placeholder.metric(MAIN_LABELS["current_frame"], 1)
                self.target_count_placeholder.metric(MAIN_LABELS["target_count"], len(detInfo))
                self.detection_time_placeholder.metric(MAIN_LABELS["detection_time"], self.detection_time)
                
                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_image, (self.display_width, self.display_height))
                
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_file.name}")
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {self.uploaded_file.name}")
                    if hasattr(self, 'image_placeholder_res'):
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_file.name}")
                
                # 添加到日志表
                self.logTable.add_frames(image, detInfo, processed_image, self.uploaded_file.name)
                
                status_info.write(STATUS_MESSAGES["updating_interface"])
                single_progress.progress(0.9)
                
                # 立即更新session state以确保UI同步
                st.session_state['saved_images_ini'] = self.logTable.saved_images_ini.copy()
                st.session_state['saved_images'] = self.logTable.saved_images.copy()
                st.session_state['saved_names'] = self.logTable.saved_names.copy()
                # 同步每张图片的目标信息
                if hasattr(self.logTable, 'saved_targets_info'):
                    st.session_state['saved_targets_info'] = self.logTable.saved_targets_info.copy()
                
                # 确保索引重置为0
                st.session_state['image_play_index'] = 0
                
                # 更新历史日志显示
                if hasattr(self, 'log_table_placeholder'):
                    self.logTable.update_table(self.log_table_placeholder)
                
                single_progress.progress(1.0)
                status_info.success(STATUS_MESSAGES["single_image_detection_complete"].format(count=len(detInfo), time=self.detection_time))

                st.success(STATUS_MESSAGES["single_image_complete"])
                # 立即刷新页面，让selectbox自动更新
                st.rerun()
                
                # 立即显示检测结果
                self.toggle_comboBox(0)
                
                st.success(STATUS_MESSAGES["image_detection_complete"])
                
            except Exception as e:
                st.error(STATUS_MESSAGES["single_image_processing_error"].format(error=str(e)))

    def _process_video_input(self):
        """
        处理视频输入
        """
        if not hasattr(self, 'uploaded_video') or not self.uploaded_video:
            st.warning(STATUS_MESSAGES["upload_video_first"])
            return
            
        self.logTable.clear_frames()
        self.progress_bar.progress(0)
        self.close_flag = self.close_placeholder.button(label=BUTTON_TEXTS["stop"])
        
        try:
            if isinstance(self.uploaded_video, list):
                # 处理多个视频文件
                for idx, uploaded_video in enumerate(self.uploaded_video):
                    if self.close_flag:
                        break
                    self._process_single_video(uploaded_video, idx)
            else:
                # 处理单个视频文件
                self._process_single_video(self.uploaded_video, 0)
                
        except Exception as e:
            st.error(STATUS_MESSAGES["video_processing_error"].format(error=str(e)))

    def _process_single_video(self, video_file, video_index):
        """处理单个视频文件"""
        try:
            # 创建临时文件
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            tfile.write(video_file.read())
            tfile.flush()
            
            cap = cv2.VideoCapture(tfile.name)
            if not cap.isOpened():
                st.error(STATUS_MESSAGES["video_open_failed"].format(video_name=video_file.name))
                return
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            current_frame = 0
            
            st.info(STATUS_MESSAGES["video_processing_start"].format(video_name=video_file.name, total_frames=total_frames))
            
            while cap.isOpened() and not self.close_flag and current_frame < total_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)
                
                # 进行检测
                framecopy = processed_frame.copy()
                current_time = current_frame / fps if fps > 0 else 0
                time_str = f"{int(current_time//3600):02d}:{int((current_time%3600)//60):02d}:{int(current_time%60):02d}"
                
                image, detInfo, _ = self.frame_process(framecopy, f"{video_file.name}_{current_frame}", video_time=time_str)
                
                # 更新状态
                st.session_state['current_frame_count'] = current_frame + 1
                st.session_state['current_target_count'] = len(detInfo)
                st.session_state['current_detection_time'] = self.detection_time
                
                # 更新显示
                self.frame_count_placeholder.metric(MAIN_LABELS["current_frame"], current_frame + 1)
                self.target_count_placeholder.metric(MAIN_LABELS["target_count"], len(detInfo))
                self.detection_time_placeholder.metric(MAIN_LABELS["detection_time"], self.detection_time)
                
                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))
                
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {video_file.name}")
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {video_file.name}")
                    if hasattr(self, 'image_placeholder_res'):
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {video_file.name}")
                
                # 添加到日志表
                self.logTable.add_frames(image, detInfo, processed_frame, f"{video_file.name}_{current_frame}")
                
                # 更新进度条
                progress = int((current_frame / total_frames) * 100)
                self.progress_bar.progress(progress)
                
                current_frame += 1
                
            cap.release()
            os.unlink(tfile.name)  # 删除临时文件
            
        except Exception as e:
            st.error(STATUS_MESSAGES["single_video_processing_error"].format(video_name=video_file.name, error=str(e)))

    def _process_camera_input(self, camera_id):
        """
        处理摄像头输入
        """
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                st.error(STATUS_MESSAGES["camera_open_failed"].format(camera_id=camera_id))
                return
            
            st.info(STATUS_MESSAGES["camera_started"].format(camera_id=camera_id))
            self.close_flag = self.close_placeholder.button(label=BUTTON_TEXTS["stop"])
            
            frame_count = 0
            while cap.isOpened() and not self.close_flag:
                ret, frame = cap.read()
                if not ret:
                    st.error(STATUS_MESSAGES["camera_read_frame_failed"])
                    break
                
                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)
                
                # 进行检测
                framecopy = processed_frame.copy()
                image, detInfo, _ = self.frame_process(framecopy, f"camera_{frame_count}")
                
                # 更新状态
                st.session_state['current_frame_count'] = frame_count + 1
                st.session_state['current_target_count'] = len(detInfo)
                st.session_state['current_detection_time'] = self.detection_time
                
                # 更新显示
                self.frame_count_placeholder.metric(MAIN_LABELS["current_frame"], frame_count + 1)
                self.target_count_placeholder.metric(MAIN_LABELS["target_count"], len(detInfo))
                self.detection_time_placeholder.metric(MAIN_LABELS["detection_time"], self.detection_time)
                
                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))
                
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption=SIDEBAR_LABELS["camera_detection_view"])
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption=SIDEBAR_LABELS["camera_original_view"])
                    if hasattr(self, 'image_placeholder_res'):
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=SIDEBAR_LABELS["camera_detection_view"])
                
                # 添加到日志表
                self.logTable.add_frames(image, detInfo, processed_frame, f"camera_{frame_count}")
                
                frame_count += 1
                time.sleep(0.1)  # 控制帧率
                
            cap.release()
            
        except Exception as e:
            st.error(STATUS_MESSAGES["camera_processing_error"].format(error=str(e)))

    def _process_rtsp_input(self, rtsp_url):
        """
        处理RTSP/RTMP流输入
        """
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                st.error(STATUS_MESSAGES["rtsp_connection_failed"].format(rtsp_url=rtsp_url))
                return

            st.info(STATUS_MESSAGES["rtsp_connected"].format(rtsp_url=rtsp_url))
            self.close_flag = self.close_placeholder.button(label=BUTTON_TEXTS["stop"])
            
            frame_count = 0
            while cap.isOpened() and not self.close_flag:
                ret, frame = cap.read()
                if not ret:
                    st.warning(STATUS_MESSAGES["rtsp_stream_interrupted"])
                    time.sleep(2)
                    continue
                
                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)
                
                # 进行检测
                framecopy = processed_frame.copy()
                image, detInfo, _ = self.frame_process(framecopy, f"rtsp_{frame_count}")
                
                # 更新状态
                st.session_state['current_frame_count'] = frame_count + 1
                st.session_state['current_target_count'] = len(detInfo)
                st.session_state['current_detection_time'] = self.detection_time
                
                # 更新显示
                self.frame_count_placeholder.metric(MAIN_LABELS["current_frame"], frame_count + 1)
                self.target_count_placeholder.metric(MAIN_LABELS["current_target"], len(detInfo))
                self.detection_time_placeholder.metric(MAIN_LABELS["current_detection_time"], self.detection_time)

                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))
                
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption=SIDEBAR_LABELS["rtsp_detection_view"])
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption=SIDEBAR_LABELS["rtsp_original_view"])
                    if hasattr(self, 'image_placeholder_res'):
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=SIDEBAR_LABELS["rtsp_detection_view"])

                # 添加到日志表
                self.logTable.add_frames(image, detInfo, processed_frame, f"rtsp_{frame_count}")
                
                frame_count += 1
                time.sleep(0.05)  # 控制帧率
                
            cap.release()
            
        except Exception as e:
            st.error(STATUS_MESSAGES["rtsp_processing_error"].format(error=str(e)))
