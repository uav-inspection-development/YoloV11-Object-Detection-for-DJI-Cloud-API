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
from license_features import DEFAULT_FEATURES, get_enabled_task_types, is_feature_enabled
from log import ResultLogger, LogTable
from model import Web_Detector
from chinese_name_list import (
    EL_class_colors,
    Thermo_class_colors,
    Visible_class_colors,
    Segmentation_class_colors,
    Other_class_colors,
    get_class_name,
)
from ui_style import def_css_html
from utils import (
    is_black_and_white,
    save_uploaded_file,
    concat_results,
    load_default_image,
    get_camera_names,
    draw_detections,
    save_chinese_image,
    format_time,
    convert_to_pseudo_colorizer,
    camera_undistortion,
    auto_undistort_image,
    rotate_image,
    auto_keystone_correction,
    enhance_texture,
    fill_largest_polygon_white,
    extract_gps_info,
    compute_inclusion_relations,
    compute_missing_panels,
    compute_misaligned_panels,
)
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
from streamlit_config import (
    optimize_streamlit_performance,
    setup_image_optimization,
    add_performance_css,
)

# 📝 命名配置模块导入
from naming_config import (
    # 系统配置
    get_system_info,
    set_language,
    get_current_language,
    available_languages,
    # 工具函数
    get_detection_message,
    get_file_message,
    get_video_message,
    get_camera_message,
    get_rtsp_message,
    get_model_message,
    get_warning_message,
    get_general_message,
    get_export_message,
    get_statistic_message,
    get_metric_label,
    get_table_column,
    get_system_message,
    get_gps_message,
    get_report_field,
    get_ui_message,
    generate_filename,
    # UI 获取函数
    get_sidebar_header,
    get_sidebar_label,
    get_sidebar_option,
    get_sidebar_hint,
    get_main_header,
    get_main_label,
    get_main_option,
    get_button_text,
    get_image_display_label,
    get_about_content,
    get_statistic_label,
    get_status_message,
    get_system_default,
)
from image_optimizer import (
    get_image_optimizer,
    optimize_image_display,
    process_uploaded_images,
)


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
    if processing_params.get("enable_pseudo_color") and is_black_and_white(image):
        image = convert_to_pseudo_colorizer(
            image,
            contrast=processing_params.get("contrast", 1.0),
            brightness=processing_params.get("brightness", 0),
        )

    if processing_params.get("enable_rotate_correction"):
        image = rotate_image(
            image,
            angle_x=processing_params.get("rot_angle_x", 0),
            angle_y=processing_params.get("rot_angle_y", 0),
            zoom_factor=processing_params.get("keystone_scale", 1.0),
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
        return get_system_info("version_info_not_found")

    def get_version_string():
        return get_system_info("unknown_version")


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

    def __init__(self, from_streamlit=False, api_params=None, enabled_features=None):
        """
        初始化光伏云组件检测系统的参数。
        """
        if from_streamlit and os.getenv("ENABLE_OAUTH") == "TRUE":
            CLIENT_ID = os.getenv("CLIENT_ID")
            CLIENT_SECRET = os.getenv("CLIENT_SECRET")
            OAUTH2_TOKEN_URL = os.getenv("OAUTH2_TOKEN_URL")

            # 验证环境变量是否存在
            if not OAUTH2_TOKEN_URL or not CLIENT_ID or not CLIENT_SECRET:
                st.error(get_general_message("env_vars_missing"))
                st.stop()

            # 获取 OAuth2 令牌
            access_token = get_access_token(OAUTH2_TOKEN_URL, CLIENT_ID, CLIENT_SECRET)
            if not access_token:
                st.error(get_general_message("oauth_token_failed"))
                st.stop()

        self.from_streamlit = from_streamlit
        self.api_params = api_params or {}
        self.enabled_features = enabled_features or DEFAULT_FEATURES
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
        self.cls_name = get_class_name("Visible")
        self.detect_class_color = Visible_class_colors
        self.colors = [
            self.detect_class_color.get(class_name, (0, 255, 0))
            for class_name in self.cls_name.values()
        ]
        self.selected_class_ids = None  # 选定的类别索引

        # 设置页面标题
        self.title = get_system_info("title")
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
                unsafe_allow_html=True,
            )

        # 初始化检测相关的配置参数
        self.model_type = get_system_default("model_type_detection")
        self.conf_threshold = 0.15  # 默认置信度阈值
        self.iou_threshold = 0.5  # 默认IOU阈值
        self.image_type = get_system_default("image_type_visible")  # 图像类型

        # 初始化检测类别相关的配置参数
        self.available_classes = None  # 可用的检测类别
        self.available_class_keys = None  # 可用的检测类别键
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
        self.image_enhancement_method = get_system_default(
            "image_enhancement_none"
        )  # 图像增强方法

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
        self.selected_targets = []  # 多选框选中项
        self.progress_bar = None  # 用于显示的进度条
        self.export_format = "CSV"  # 导出格式
        self.clear_after_export = False  # 导出后清空检测结果

        self.frame_count_placeholder = None  # 帧计数显示区域
        self.fps_placeholder = None  # FPS显示区域
        self.target_count_placeholder = None  # 目标计数显示区域
        self.detection_time_placeholder = None  # 检测时间显示区域
        self.category_count_placeholder = None  # 类别计数表格区域
        self.selectbox_placeholder = None
        # GPS 信息指标占位符
        self.gps_lat_placeholder = None
        self.gps_lon_placeholder = None
        self.gps_alt_placeholder = None
        self.gps_time_placeholder = None
        self.inclusion_table_placeholder = None
        self.show_inclusion = False
        self.show_missing_panel = False
        self.show_misaligned_panel = False

        self.new_width = 1080
        self.new_height = int(self.new_width * (9 / 16))

        # 初始化FPS和视频时间指针
        self.FPS = 30
        self.timenow = 0

        # 初始化相机参数
        self.undistortion_method = get_system_default("undistortion_none")
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_file = None
        self.image_k1 = 0.0  # 畸变系数

        self.csv_output_path = abs_path("../output/logs/", path_type="current")
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 初始化日志数据保存路径
        self.saved_log_data = os.path.join(
            self.csv_output_path, f"log_table_data_{current_time}.csv"
        )

        # 初始化
        self.available_cameras = get_camera_names()
        self.logTable = LogTable(self.saved_log_data)
        self.model = Web_Detector()
        self.colors = []

        # 确保 logTable 属性始终存在
        if not hasattr(self, "logTable"):
            self.logTable = LogTable(self.saved_log_data)

        if "current_frame_count" not in st.session_state:
            st.session_state["current_frame_count"] = 0
        if "current_fps" not in st.session_state:
            st.session_state["current_fps"] = 0
        if "current_target_count" not in st.session_state:
            st.session_state["current_target_count"] = 0
        if "current_detection_time" not in st.session_state:
            st.session_state["current_detection_time"] = 0

        if "saved_images_ini" not in st.session_state:
            # 初始化保存的原始图像列表
            st.session_state["saved_images_ini"] = []
        if "saved_images" not in st.session_state:
            # 初始化保存的结果图像列表
            st.session_state["saved_images"] = []
        if "saved_names" not in st.session_state:
            # 初始化保存的图像名称列表
            st.session_state["saved_names"] = []

        if self.from_streamlit:
            self.setup_sidebar()  # 初始化侧边栏布局
        else:
            self.load_api_params()  # 加载API参数

    def load_api_params(self):
        """
        用于 Flask 模式，根据 API 提供的参数设置实例变量。
        """
        # 根据 API 提供的参数设置实例变量
        self.csv_output_path = self.api_params.get(
            "csv_output_path", abs_path("../output/logs/", path_type="current")
        )

        # 确保路径以斜杠结尾
        if not self.csv_output_path.endswith(os.sep):
            self.csv_output_path += os.sep

        # 根据用户输入的路径设置日志文件路径
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.saved_log_data = os.path.join(
            self.csv_output_path, f"log_table_data_{current_time}.csv"
        )

        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(self.csv_output_path):
            os.makedirs(self.csv_output_path)

        self.available_cameras = get_camera_names()
        self.logTable = LogTable(self.saved_log_data)
        self.model = Web_Detector()

        self.conf_threshold = float(self.api_params.get("conf_threshold", 0.15))
        self.iou_threshold = float(self.api_params.get("iou_threshold", 0.25))
        self.model_type = self.api_params.get(
            "model_type", get_system_default("model_type_detection")
        )
        self.image_type = self.api_params.get(
            "image_type", get_system_default("image_type_visible")
        )
        self.selected_classes = self.api_params.get(
            "selected_classes", list(get_class_name("Visible").keys())
        )
        self.enable_pseudo_color = self.api_params.get("enable_pseudo_color", False)
        self.enable_rotate_correction = self.api_params.get(
            "enable_rotate_correction", False
        )
        self.enable_auto_keystone_correction = self.api_params.get(
            "enable_auto_keystone_correction", False
        )
        self.enable_background_fill = self.api_params.get(
            "enable_background_fill", False
        )
        self.image_enhancement_method = self.api_params.get(
            "image_enhancement_method", get_system_default("image_enhancement_none")
        )
        self.undistortion_method = self.api_params.get(
            "undistortion_method", get_system_default("undistortion_none")
        )

        # 通过API方式上传相机标定文件
        if self.undistortion_method == get_system_default("undistortion_camera_calc"):
            calibration_file = self.api_params.get("calibration_file", None)
            if calibration_file is not None:
                try:
                    # calibration_file 可以是文件路径或文件内容
                    if isinstance(calibration_file, str) and os.path.exists(
                        calibration_file
                    ):
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
                    self.calibration_file = (
                        calibration_file
                        if isinstance(calibration_file, str)
                        else "api_upload"
                    )
                    print(get_camera_message("camera_calibration_success"))
                except Exception as e:
                    print(get_camera_message("camera_calibration_failed", error=str(e)))
                    self.camera_matrix = None
                    self.dist_coeffs = None
                    self.calibration_file = None
            else:
                self.camera_matrix = None
                self.dist_coeffs = None
                self.calibration_file = None
        elif self.undistortion_method == get_system_default("undistortion_manual"):
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
            self.scale_factor_keystone = float(
                self.api_params.get("scale_factor_keystone", 0.1)
            )

        if self.enable_background_fill:
            self.scale_factor_fill = float(
                self.api_params.get("scale_factor_fill", 0.1)
            )

        # 设置类别标签
        if self.model_type == get_system_default("model_type_segmentation"):
            self.cls_name = get_class_name("Segmentation")
            self.detect_class_color = Segmentation_class_colors
        else:
            if self.image_type == get_system_default("image_type_thermal"):
                self.cls_name = get_class_name("Thermal")
                self.detect_class_color = Thermo_class_colors
            elif self.image_type == get_system_default("image_type_el"):
                self.cls_name = get_class_name("EL")
                self.detect_class_color = EL_class_colors
            elif self.image_type == get_system_default("image_type_visible"):
                self.cls_name = get_class_name("Visible")
                self.detect_class_color = Visible_class_colors
            else:
                self.cls_name = get_class_name("Other")
                self.detect_class_color = Other_class_colors

        # 重新加载模型
        if self.model_type == get_system_default("model_type_detection"):
            if self.image_type == get_system_default("image_type_thermal"):
                model_path = abs_path(
                    "../weights/yolo11s-thermo.pt", path_type="current"
                )
            elif self.image_type == get_system_default("image_type_el"):
                model_path = abs_path("../weights/yolo11s-el.pt", path_type="current")
            elif self.image_type == get_system_default("image_type_visible"):
                model_path = abs_path(
                    "../weights/yolo11s-visible.pt", path_type="current"
                )
            else:
                model_path = abs_path("../weights/yolo11s.pt", path_type="current")
        else:
            if self.image_type == get_system_default("image_type_thermal"):
                model_path = abs_path(
                    "../weights/yolo11s-thermo-seg.pt", path_type="current"
                )
            elif self.image_type == get_system_default("image_type_visible"):
                model_path = abs_path(
                    "../weights/yolo11s-visible-seg.pt", path_type="current"
                )
            else:
                print("Invalid image type for segmentation task.")

        try:
            self.model.load_model(model_path=model_path)
            # 确保类别排序一致
            sorted_cls_name = {
                name: self.cls_name[name]
                for name in self.model.names
                if name in self.cls_name
            }
            self.cls_name = sorted_cls_name

            # 重新初始化颜色列表，确保顺序与模型类别一致
            for class_name in self.model.names:
                if class_name in self.detect_class_color:
                    # 如果已定义颜色，使用定义的颜色
                    self.colors.append(self.detect_class_color[class_name])
                else:
                    # 如果未定义颜色，填充随机颜色
                    self.colors.append(
                        (
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                        )
                    )

            # 确保颜色列表长度与模型类别一致
            if len(self.colors) != len(self.model.names):
                st.warning(get_warning_message("color_list_warning"))

        except Exception as e:
            print(f"无法加载模型文件，请检查文件路径或文件是否存在！错误信息: {str(e)}")

    def setup_page(self):
        """
        设置 Streamlit 页面标题和布局。
        """
        # 居中显示标题
        st.markdown(
            f'<h1 style="text-align: center;">{self.title}</h1>', unsafe_allow_html=True
        )

    def show_about_section(self):
        """
        在 Streamlit UI 的右上角显示关于部分。
        """
        # 获取版本信息字符串
        version_string = get_version_string()

        with st.sidebar.expander(
            get_sidebar_header("about_version").format(version_string=version_string),
            expanded=False,
        ):
            # 主标题和描述
            st.subheader(get_about_content('title'))
            st.markdown(get_about_content('description'))

            # 功能特点
            st.subheader(get_about_content('features_title'))
            st.markdown(get_about_content('features'))

            # 使用技术
            st.subheader(get_about_content('tech_title'))
            st.markdown(get_about_content('technologies'))

            # 显示Git版本信息
            if GIT_INFO_AVAILABLE:
                st.markdown("---")
                git_info_md = format_git_info_for_about()
                st.markdown(git_info_md)

            # 作者和联系方式
            st.markdown("---")
            st.subheader(get_about_content('author_title'))
            st.markdown(get_about_content('author'))
            st.subheader(get_about_content('contact_title'))
            st.markdown(get_about_content('contact'))

    def setup_sidebar(self):
        """
        设置 Streamlit 侧边栏。

        在侧边栏中配置模型设置、摄像头选择以及识别项目设置等选项。
        """
        # Language selection
        current_lang = get_current_language()
        lang = st.sidebar.selectbox(
            get_sidebar_label("language"),
            options=available_languages,
            index=available_languages.index(current_lang),
        )

        # 检查语言是否改变，如果改变则设置新语言并刷新页面
        if lang != current_lang:
            set_language(lang)
            st.rerun()

        st.sidebar.title(get_sidebar_header("settings_menu"))

        # Add the About section to the sidebar
        self.show_about_section()

        # 添加登录设置
        st.sidebar.header(get_sidebar_header("login_settings"))
        if st.sidebar.button(get_sidebar_label("logout_button")):
            st.session_state.clear()
            if os.path.exists("login_cache.json"):
                os.remove("login_cache.json")
            st.rerun()

        # 添加显示设置
        st.sidebar.header(get_sidebar_header("display_settings"))

        # 添加固定比例选项
        aspect_options = get_sidebar_option("aspect_ratios")
        aspect_ratio = st.sidebar.selectbox(
            get_sidebar_label("aspect_ratio_selection"),
            options=aspect_options,
            index=0,
        )
        if aspect_ratio == aspect_options[0]:
            ratio = 16 / 9
        elif aspect_ratio == aspect_options[1]:
            ratio = 4 / 3
        else:
            ratio = None  # Free

        # 根据选择的比例调整宽度和高度
        if ratio:
            # 用户输入高度时自动调整宽度
            self.new_height = st.sidebar.number_input(
                get_sidebar_label("display_height_input"),
                min_value=100,
                max_value=2160,
                value=1080,
                step=10,
            )
            self.new_width = int(self.new_height * ratio)
            st.sidebar.number_input(
                get_sidebar_label("display_width_input"),
                value=self.new_width,
                disabled=True,
            )
        else:
            # 自由调整模式
            self.new_width = st.sidebar.number_input(
                get_sidebar_label("display_width_input_free"),
                min_value=100,
                max_value=3840,
                value=1080,
                step=10,
            )
            self.new_height = st.sidebar.number_input(
                get_sidebar_label("display_height_input_free"),
                min_value=100,
                max_value=2160,
                value=720,
                step=10,
            )

        # 添加 CSV 输出路径设置
        st.sidebar.header(get_sidebar_header("log_path_settings"))
        self.csv_output_path = st.sidebar.text_input(
            get_sidebar_label("log_save_path"),
            value=abs_path("../output/logs", path_type="current"),  # 默认路径
            placeholder="例如：D:/output/logs",
        )

        # 确保路径以斜杠结尾
        if not self.csv_output_path.endswith(os.sep):
            self.csv_output_path += os.sep

        st.sidebar.header(get_sidebar_header("export_format_settings"))
        self.export_format = st.sidebar.radio(
            get_sidebar_label("export_format_selection"),
            options=get_sidebar_option("export_formats"),
            index=0,
            help=get_sidebar_hint("export_format_hint").format(
                format="所选格式", path=self.csv_output_path
            )
        )

        # 添加导出后清空检测结果选项
        self.clear_after_export = st.sidebar.checkbox(
            get_sidebar_label("clear_after_export"),
            value=False,
            help=get_sidebar_hint("clear_after_export_hint")
        )

        # 添加GPS经纬度解析选项
        self.enable_gps_parsing = st.sidebar.checkbox(
            get_sidebar_label("enable_gps_parsing"),
            value=True,
            help=get_sidebar_hint("gps_parsing_help") + "\n\n" + get_sidebar_hint("gps_parsing_hint")
        )

        export_options = get_sidebar_option("export_formats")
        # 根据用户选择的导出格式设置文件后缀
        if self.export_format == export_options[0]:
            file_suffix = ".docx"
        elif self.export_format == export_options[1]:
            file_suffix = ".csv"
        elif self.export_format == export_options[2]:
            file_suffix = ".xlsx"
        elif self.export_format == export_options[3]:
            file_suffix = ".json"
        else:
            file_suffix = ".txt"

        # 根据用户输入的路径设置日志文件路径
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.saved_log_data = os.path.join(
            self.csv_output_path, f"log_table_data_{current_time}{file_suffix}"
        )

        # 检查目录是否存在，如果不存在则创建
        if not os.path.exists(self.csv_output_path):
            os.makedirs(self.csv_output_path)

        # Streamlit模式初始化 session state
        if "logTable" not in st.session_state:
            # 如果在 session state 中不存在logTable，创建一个新的LogTable实例
            st.session_state["logTable"] = LogTable(self.saved_log_data)
        if "available_cameras" not in st.session_state:
            # 获取或更新可用摄像头列表
            st.session_state["available_cameras"] = get_camera_names()
        if "model" not in st.session_state:
            # 加载或创建模型实例
            st.session_state["model"] = Web_Detector()

        self.available_cameras = st.session_state["available_cameras"]
        if len(self.available_cameras) == 1:
            st.write(get_camera_message("no_camera_found"))

        # 初始化或获取识别结果的表格
        self.logTable = st.session_state["logTable"]
        self.model = st.session_state["model"]

        st.sidebar.header(get_sidebar_header("detection_thresholds"))
        # 置信度阈值的滑动条
        self.conf_threshold = float(
            st.sidebar.slider(
                get_sidebar_label("conf_threshold_slider"),
                min_value=0.0,
                max_value=1.0,
                value=0.15,
                help=get_sidebar_hint("conf_threshold_hint")
            )
        )
        # IOU阈值的滑动条
        self.iou_threshold = float(
            st.sidebar.slider(
                get_sidebar_label("iou_threshold_slider"),
                min_value=0.0,
                max_value=1.0,
                value=0.25,
                help=get_sidebar_hint("iou_threshold_hint")
            )
        )
        # 设置侧边栏的模型设置部分
        st.sidebar.header(get_sidebar_header("model_settings"))
        # 选择模型类型的下拉菜单
        available_task_types = get_sidebar_option("task_types")
        task_options = get_enabled_task_types(available_task_types, self.enabled_features)
        if not task_options:
            st.error(get_model_message("no_licensed_task_types"))
            st.stop()

        self.model_type = st.sidebar.radio(
            get_sidebar_label("task_type_selection"),
            options=task_options,
            index=0,
        )

        available_options = []
        # 添加提示信息
        if self.model_type == get_system_default("model_type_detection"):
            # 检测任务也应该有矩形框选项
            self.rectangle_bounding_output = st.sidebar.checkbox(
                get_sidebar_label("rectangle_output_checkbox"),
                value=True,
                help=get_sidebar_hint("detection_task_hint")
            )
            available_options = [
                get_system_default("image_type_el"),
                get_system_default("image_type_thermal"),
                get_system_default("image_type_visible"),
                get_system_default("image_type_other"),
            ]
        elif self.model_type == get_system_default("model_type_segmentation"):
            self.rectangle_bounding_output = st.sidebar.checkbox(
                get_sidebar_label("rectangle_output_checkbox"),
                value=True,
                help=get_sidebar_hint("segmentation_task_hint")
            )

            self.show_inclusion = st.sidebar.checkbox(
                get_sidebar_label("show_inclusion_relationship"),
                value=False,
                help=get_sidebar_hint("inclusion_relationship_hint")
            )

            self.show_missing_panel = st.sidebar.checkbox(
                get_sidebar_label("show_missing_panel"),
                value=False,
                help=get_sidebar_hint("missing_panel_hint")
            )

            self.show_misaligned_panel = st.sidebar.checkbox(
                get_sidebar_label("show_misaligned_panel"),
                value=False,
                help=get_sidebar_hint("misaligned_panel_hint")
            )

            available_options = [
                get_system_default("image_type_thermal"),
                get_system_default("image_type_visible"),
            ]

        available_options = [opt for opt in available_options if is_feature_enabled(opt, self.enabled_features) or opt == "其他"]
        if not available_options:
            st.error(get_model_message("no_licensed_image_types"))
            st.stop()

        # 添加图像类型选择
        st.sidebar.header(get_sidebar_header("image_type_selection"))
        self.image_type = st.sidebar.radio(
            get_sidebar_label("select_image_type"),
            options=available_options,
            index=0,  # 默认选择第一个选项
            help=get_sidebar_hint("image_type_hint").format(type="选择的图像类型")
        )

        if self.model_type == get_system_default("model_type_detection"):
            if self.image_type == get_system_default("image_type_thermal"):
                self.cls_name = get_class_name("Thermal")
                self.detect_class_color = Thermo_class_colors
            elif self.image_type == get_system_default("image_type_el"):
                self.cls_name = get_class_name("EL")
                self.detect_class_color = EL_class_colors
            elif self.image_type == get_system_default("image_type_visible"):
                self.cls_name = get_class_name("Visible")
                self.detect_class_color = Visible_class_colors
            else:
                self.cls_name = get_class_name("Other")
                self.detect_class_color = Other_class_colors
        elif self.model_type == get_system_default("model_type_segmentation"):
            self.cls_name = get_class_name("Segmentation")
            self.detect_class_color = Segmentation_class_colors

        # 设置侧边栏的选择需要检测的目标类别部分，默认选择所有类别
        st.sidebar.header(get_sidebar_header("target_class_selection"))
        self.available_classes = list(self.cls_name.values())
        self.available_class_keys = list(self.cls_name.keys())
        selected_chinese_classes = st.sidebar.multiselect(
            get_sidebar_label("select_detection_or_segmentation_type"),
            options=self.available_classes,
            default=self.available_classes,  # 默认选择所有类别
            help=get_sidebar_hint("selected_classes_hint").format(classes="所选类别")
        )

        # 将选定的类别转换为索引
        self.selected_class_ids = [
            idx
            for idx, name in enumerate(self.model.names)
            if name in selected_chinese_classes
        ]

        # 正确映射中文名称到英文名称
        self.selected_classes = [
            english_name
            for english_name, chinese_name in self.cls_name.items()
            if chinese_name in selected_chinese_classes
        ]

        # 选择模型文件类型，可以是默认的或者自定义的
        st.sidebar.header(get_sidebar_header("model_file_settings"))
        model_options = get_sidebar_option("model_settings")
        model_file_option = st.sidebar.radio(
            get_sidebar_label("model_settings"),
            options=model_options,
            index=0,
        )
        if model_file_option == model_options[1]:
            # 如果选择自定义模型文件，则提供文件上传器
            model_file = st.sidebar.file_uploader(
                get_sidebar_label("select_pt_file"), type="pt"
            )

            # 如果上传了模型文件，则保存并加载该模型
            if model_file is not None:
                self.custom_model_file = save_uploaded_file(model_file)
                try:
                    self.model.load_model(model_path=self.custom_model_file)
                except Exception as e:
                    st.sidebar.error(
                        get_model_message("model_load_error", error=str(e))
                    )
                # 检查模型类别是否与选定类别一致
                if set(self.model.names) != set(self.available_class_keys):
                    st.sidebar.error(get_model_message("model_class_mismatch"))
                else:
                    self.colors = [
                        self.detect_class_color.get(class_name, (0, 255, 0))
                        for class_name in self.cls_name.values()
                    ]
        elif model_file_option == model_options[0]:
            if self.model_type == get_system_default("model_type_detection"):
                if self.image_type == get_system_default("image_type_thermal"):
                    model_path = abs_path(
                        "../weights/yolo11s-thermo.pt", path_type="current"
                    )
                elif self.image_type == get_system_default("image_type_el"):
                    model_path = abs_path(
                        "../weights/yolo11s-el.pt", path_type="current"
                    )
                elif self.image_type == get_system_default("image_type_visible"):
                    model_path = abs_path(
                        "../weights/yolo11s-visible.pt", path_type="current"
                    )
                else:
                    model_path = abs_path("../weights/yolo11s.pt", path_type="current")
            else:
                if self.image_type == get_system_default("image_type_thermal"):
                    model_path = abs_path(
                        "../weights/yolo11s-thermo-seg.pt", path_type="current"
                    )
                elif self.image_type == get_system_default("image_type_visible"):
                    model_path = abs_path(
                        "../weights/yolo11s-visible-seg.pt", path_type="current"
                    )
                else:
                    st.sidebar.error(get_model_message("unsupported_image_type"))

            try:
                self.model.load_model(model_path=model_path)
                # 确保类别排序一致
                sorted_cls_name = {
                    name: self.cls_name[name]
                    for name in self.model.names
                    if name in self.cls_name
                }
                self.cls_name = sorted_cls_name

                # 重新初始化颜色列表，确保顺序与模型类别一致
                for class_name in self.model.names:
                    if class_name in self.detect_class_color:
                        # 如果已定义颜色，使用定义的颜色
                        self.colors.append(self.detect_class_color[class_name])
                    else:
                        # 如果未定义颜色，填充随机颜色
                        self.colors.append(
                            (
                                random.randint(0, 255),
                                random.randint(0, 255),
                                random.randint(0, 255),
                            )
                        )

                # 确保颜色列表长度与模型类别一致
                if len(self.colors) != len(self.model.names):
                    st.warning(get_warning_message("color_list_warning"))

            except Exception as e:
                st.sidebar.error(
                    get_model_message("default_model_load_error", error=str(e))
                )

            # 检查类别是否完全一致
            if set(self.model.names) != set(self.available_class_keys):
                # 如果 chinese_name_list 的类别比模型的类别少，则以 chinese_name_list 为准
                if len(self.available_class_keys) < len(self.model.names):
                    self.model.names = [
                        name
                        for name in self.model.names
                        if name in self.available_class_keys
                    ]
                # 如果 chinese_name_list 的类别比模型的类别多，则以模型为准
                else:
                    self.available_class_keys = [
                        key
                        for key in self.available_class_keys
                        if key in self.model.names
                    ]

                # 重新检查类别是否一致
                missing_in_model = set(self.available_class_keys) - set(
                    self.model.names
                )
                missing_in_selected = set(self.model.names) - set(
                    self.available_class_keys
                )

                # 输出缺失的类别
                print(f"模型类别: {self.model.names}")
                print(f"选定类别: {self.available_class_keys}")
                print(f"模型中缺失的类别: {missing_in_model}")
                print(f"选定类别中缺失的类别: {missing_in_selected}")

                # 在 Streamlit 侧边栏显示错误信息
                st.sidebar.warning(get_model_message("model_class_auto_adjusted"))
            else:
                # 为模型中的类别重新分配颜色
                self.colors = [
                    self.detect_class_color.get(
                        class_name, [random.randint(0, 255) for _ in range(3)]
                    )
                    for class_name in self.model.names
                ]

        # 设置侧边栏的摄像头和 RTSP/RTMP 配置部分
        st.sidebar.header(get_sidebar_header("input_source_settings"))
        # 选择输入源类型：无输入，摄像头或 RTSP/RTMP 流
        input_options = get_sidebar_option("input_sources")
        self.input_source = st.sidebar.radio(
            get_sidebar_label("input_source_selection"),
            options=input_options,
            index=0,
        )

        if "file_key" not in st.session_state:
            st.session_state["file_key"] = str(random.random())

        if self.input_source == input_options[4]:
            # 选择摄像头的下拉菜单
            self.selected_camera = st.sidebar.selectbox(
                get_sidebar_label("camera_selection"),
                self.available_cameras,
                help=get_sidebar_hint("camera_hint")
            )
        elif self.input_source == input_options[5]:
            # 输入 RTSP/RTMP 地址
            self.rtsp_input_url = st.sidebar.text_input(
                get_sidebar_label("rtsp_input"),
                placeholder=get_sidebar_label("rtsp_input_example"),
                help=get_sidebar_hint("rtsp_hint")
            )
        elif self.input_source == input_options[0]:
            self.uploaded_file = st.sidebar.file_uploader(
                get_sidebar_label("upload_images"),
                type=["jpg", "png", "jpeg"],
                accept_multiple_files=True,
                key=st.session_state["file_key"],
                help=get_sidebar_hint("image_detection_hint")
            )

            # 显示上传状态和进度
            if self.uploaded_file:
                num_files = len(self.uploaded_file)
                st.sidebar.success(
                    get_sidebar_hint("image_upload_success").format(count=num_files)
                )

                # 显示文件列表
                with st.sidebar.expander(
                    get_sidebar_label("display_uploaded_files"), expanded=False
                ):
                    for i, file in enumerate(self.uploaded_file[:10]):  # 最多显示前10个
                        file_size = len(file.getvalue()) / 1024  # KB
                        st.write(f"{i + 1}. {file.name} ({file_size:.1f} KB)")
                    if num_files > 10:
                        st.write(
                            get_sidebar_hint("more_files_remaining").format(
                                count=num_files - 10
                            )
                        )
            else:
                st.sidebar.info(get_sidebar_hint("image_upload_hint"))
        elif self.input_source == input_options[1]:
            default_types = ["jpg", "jpeg", "png"]
            image_types = st.sidebar.multiselect(
                get_sidebar_label("select_image_type"),
                options=["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"],
                default=default_types,
            )

            # Tkinter文件夹选择器按钮
            if st.sidebar.button(get_sidebar_label("select_image_folder")):
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", 1)
                folder_path = filedialog.askdirectory(master=root)
                root.destroy()
                if folder_path:
                    st.session_state["image_folder_path"] = folder_path

            folder_path = st.sidebar.text_input(
                get_sidebar_label("input_folder_path"),
                value=st.session_state.get("image_folder_path", ""),
                placeholder=get_sidebar_label("folder_path_example"),
                help=get_sidebar_hint("folder_selection_hint")
            )
            image_files = []
            if folder_path and os.path.isdir(folder_path):
                # 显示扫描进度
                with st.sidebar:
                    st.info(get_file_message("scanning_folder"))
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
                st.sidebar.success(
                    get_sidebar_hint("scanning_complete").format(count=len(image_files))
                )

                # 显示文件夹统计信息
                if image_files:
                    with st.sidebar.expander(
                        get_sidebar_label("folder_statistics"), expanded=False
                    ):
                        # 按文件类型统计
                        type_count = {}
                        for file in image_files:
                            ext = os.path.splitext(file)[1].lower()
                            type_count[ext] = type_count.get(ext, 0) + 1

                        st.write(get_statistic_message("statistics_by_type"))
                        for ext, count in type_count.items():
                            st.write(f"  {ext}: {count} 张")

                        # 显示前几个文件名
                        st.write(get_statistic_message("example_files"))
                        for i, file in enumerate(image_files[:5]):
                            st.write(f" {i + 1}. {os.path.basename(file)}")
                        if len(image_files) > 5:
                            st.write(
                                get_sidebar_hint("more_files_remaining").format(
                                    count=len(image_files) - 5
                                )
                            )

                # 转为文件对象
                self.uploaded_file = [LocalFileObj(f) for f in image_files]
            else:
                if folder_path:
                    st.sidebar.error(get_sidebar_hint("invalid_folder_path"))
                self.uploaded_file = []
        elif self.input_source == input_options[2]:
            self.uploaded_video = st.sidebar.file_uploader(
                get_sidebar_label("upload_videos"),
                type=["mp4", "avi", "mov"],
                accept_multiple_files=True,
                key=st.session_state["file_key"],
                help=get_sidebar_hint("video_detection_hint")
            )

            # 显示上传状态和进度
            if self.uploaded_video:
                num_videos = len(self.uploaded_video)
                st.sidebar.success(
                    get_sidebar_hint("video_upload_success").format(count=num_videos)
                )

                # 显示视频列表和信息
                with st.sidebar.expander(
                    get_sidebar_label("display_uploaded_video"), expanded=False
                ):
                    total_size = 0
                    for i, video in enumerate(self.uploaded_video[:5]):  # 最多显示前5个
                        video_size = len(video.getvalue()) / (1024 * 1024)  # MB
                        total_size += video_size
                        st.write(f"{i + 1}. {video.name} ({video_size:.1f} MB)")
                    if num_videos > 5:
                        st.write(
                            get_file_message(
                                "more_videos_remaining", count=num_videos - 5
                            )
                        )
                    st.write(get_statistic_message("total_size", size=total_size))
            else:
                st.sidebar.info(get_sidebar_hint("video_upload_hint"))
        elif self.input_source == input_options[3]:
            default_video_types = ["mp4", "avi", "mov"]
            video_types = st.sidebar.multiselect(
                get_sidebar_label("select_video_type"),
                options=["mp4", "avi", "mov", "mkv", "flv", "wmv"],
                default=default_video_types,
            )
            # Tkinter文件夹选择器按钮
            if st.sidebar.button(get_sidebar_label("select_video_folder")):
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes("-topmost", 1)
                folder_path = filedialog.askdirectory(master=root)
                root.destroy()
                if folder_path:
                    st.session_state["video_folder_path"] = folder_path

            folder_path = st.sidebar.text_input(
                get_sidebar_label("input_video_folder_path"),
                value=st.session_state.get("video_folder_path", ""),
                placeholder=get_sidebar_label("video_folder_path_example"),
                help=get_sidebar_hint("video_folder_selection_hint")
            )
            video_files = []
            if folder_path and os.path.isdir(folder_path):
                exts = tuple(f".{ext.lower()}" for ext in video_types)
                for root_dir, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(exts):
                            video_files.append(os.path.join(root_dir, file))
                st.sidebar.write(get_sidebar_label("total_video_count").format(count=len(video_files)))
                # 转为文件对象
                self.uploaded_video = [LocalFileObj(f) for f in video_files]
            else:
                self.uploaded_video = []

        # 清空按钮
        if st.sidebar.button(get_sidebar_label("clear_uploaded_files")):
            self.uploaded_file = None
            self.uploaded_video = None

            # 清空 file_uploader 的 key 以强制刷新组件
            st.session_state["file_key"] = str(random.random())

            # 清理与 file_uploader 有关的 session state
            for key in list(st.session_state.keys()):
                if key.startswith("file_uploader"):
                    del st.session_state[key]

            # 清空文件夹路径（图片/视频）
            if "image_folder_path" in st.session_state:
                del st.session_state["image_folder_path"]
            if "video_folder_path" in st.session_state:
                del st.session_state["video_folder_path"]

            # 显式设置文件对象为空（用于 LocalFileObj 列表）
            self.uploaded_file = []
            self.uploaded_video = []

            # 重新运行 Streamlit 应用以更新状态
            st.rerun()

            st.sidebar.success(get_sidebar_hint("clear_files_success"))

        if self.input_source in [input_options[4], input_options[5], input_options[2]]:
            # 添加视频输出和 RTSP 输出的启用复选框
            st.sidebar.header(get_sidebar_header("video_output_settings"))
            self.enable_video_output = st.sidebar.checkbox(
                get_sidebar_label("enable_video_output"), value=True
            )

        # 图像畸变校正参数设置
        st.sidebar.header(get_sidebar_header("image_processing_settings"))
        # 添加伪彩色转换选项
        self.enable_pseudo_color = st.sidebar.checkbox(
            get_sidebar_label("enable_pseudo_color"),
            value=False,
            help=get_sidebar_hint("false_color_hint")
        )
        # 如果启用伪彩色转换，显示对比度和亮度调整选项
        if self.enable_pseudo_color:
            self.image_contrast = st.sidebar.slider(
                get_sidebar_label("contrast_adjustment"),
                min_value=0.5,
                max_value=3.0,
                value=1.0,
                step=0.1,
            )
            self.image_brightness = st.sidebar.slider(
                get_sidebar_label("brightness_adjustment"),
                min_value=-255,
                max_value=255,
                value=0,
                step=1,
            )

        # 添加图像旋转校正选项
        self.enable_rotate_correction = st.sidebar.checkbox(
            get_sidebar_label("enable_rotate_correction"),
            value=False,
            help=get_sidebar_hint("rotation_correction_hint")
        )
        if self.enable_rotate_correction:
            # 滑动条调整水平和垂直旋转角度，以及缩放比例
            self.rot_angle_x = st.sidebar.slider(
                get_sidebar_label("vertical_rotation_angle"),
                min_value=-90,
                max_value=90,
                value=0,
                step=1,
            )
            self.rot_angle_y = st.sidebar.slider(
                get_sidebar_label("horizontal_rotation_angle"),
                min_value=-90,
                max_value=90,
                value=0,
                step=1,
            )
            self.keystone_scale = st.sidebar.slider(
                get_sidebar_label("scale_ratio"),
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.01,
            )

        # 添加梯形校正选项
        self.enable_auto_keystone_correction = st.sidebar.checkbox(
            get_sidebar_label("enable_auto_keystone_correction"),
            value=False,
            help=get_sidebar_hint("perspective_correction_hint")
        )
        if self.enable_auto_keystone_correction:
            # 滑动条调整最小面积比例
            self.scale_factor_keystone = st.sidebar.slider(
                get_sidebar_label("keystone_correction_min_area"),
                min_value=0.1,
                max_value=0.8,
                value=0.1,
                step=0.05,
            )

        # 添加背景填充选项
        self.enable_background_fill = st.sidebar.checkbox(
            get_sidebar_label("enable_background_fill"),
            value=False,
            help=get_sidebar_hint("background_fill_hint")
        )
        if self.enable_background_fill:
            # 滑动条调整最小面积比例
            self.scale_factor_fill = st.sidebar.slider(
                get_sidebar_label("background_fill_min_area"),
                min_value=0.1,
                max_value=0.8,
                value=0.1,
                step=0.05,
            )

        # 添加图像增强选项
        enhancement_options = get_sidebar_option("image_enhancement_methods")
        self.image_enhancement_method = st.sidebar.radio(
            get_sidebar_label("image_enhancement_method"),
            options=enhancement_options,
            index=0,
            help=get_sidebar_hint("image_enhancement_hint")
        )

        # 添加图像畸变校正选项
        undistort_options = get_sidebar_option("undistortion_methods")
        self.undistortion_method = st.sidebar.radio(
            get_sidebar_label("undistortion_method"),
            options=undistort_options,
            index=0,
            help=get_sidebar_hint("camera_calibration_hint")
        )

        if self.undistortion_method == get_system_default("undistortion_camera_calc"):
            calibration_file = st.sidebar.file_uploader(
                get_sidebar_label("upload_calibration_file"), type=["json"]
            )
            calibration_input = st.sidebar.text_area(
                get_sidebar_label("paste_calibration_params"), value="", height=150
            )
            calib_data = None
            if calibration_file is not None:
                try:
                    calib_data = json.load(calibration_file)
                    self.camera_matrix = np.array(calib_data["camera_matrix"])
                    self.dist_coeffs = np.array(calib_data["dist_coeffs"])
                    self.calibration_file = calibration_file.name
                    st.sidebar.success(get_camera_message("camera_calibration_success"))
                except Exception as e:
                    st.sidebar.error(get_camera_message("camera_calibration_failed", error=e))
            elif calibration_input.strip():
                try:
                    # 尝试先用json解析，否则用eval（仅限受信环境）
                    try:
                        calib_data = json.loads(calibration_input)
                    except Exception:
                        calib_data = eval(calibration_input, {"__builtins__": {}})
                    self.calibration_file = "sidebar_input"
                except Exception as e:
                    st.sidebar.error(get_camera_message("camera_calibration_failed", error=e))
            if calib_data is not None:
                try:
                    self.camera_matrix = np.array(calib_data["camera_matrix"])
                    self.dist_coeffs = np.array(calib_data["dist_coeffs"])
                    st.sidebar.success(get_camera_message("camera_calibration_success"))
                except Exception as e:
                    st.sidebar.error(get_camera_message("camera_calibration_failed", error=e))
                    self.camera_matrix = None
                    self.dist_coeffs = None
                    self.calibration_file = None
            else:
                self.camera_matrix = None
                self.dist_coeffs = None
                self.calibration_file = None
        elif self.undistortion_method == get_system_default("undistortion_manual"):
            # Add slider for distortion coefficient
            self.image_k1 = st.sidebar.slider(
                get_sidebar_label("adjust_distortion_coefficient"),
                min_value=-0.5,
                max_value=0.5,
                value=0.0,
                step=0.01,
                help=get_sidebar_hint("distortion_coefficient_hint")
            )

        # Apply distortion adjustment using the slider value
        if self.uploaded_file:
            if isinstance(self.uploaded_file, list):  # Handle multiple file uploads
                total_files = len(self.uploaded_file)

                # 初始化侧边栏图片预览索引
                if "sidebar_preview_index" not in st.session_state:
                    st.session_state["sidebar_preview_index"] = 0

                # 确保索引在有效范围内
                current_preview_index = min(
                    st.session_state["sidebar_preview_index"], total_files - 1
                )
                st.session_state["sidebar_preview_index"] = current_preview_index

                # 侧边栏图片预览控制
                st.sidebar.subheader(get_main_header("image_preprocessing_preview"))

                # 图片切换控件
                preview_col1, preview_col2, preview_col3 = st.sidebar.columns([1, 2, 1])

                with preview_col1:
                    if st.button(
                        "⬅️", key="sidebar_prev", disabled=(current_preview_index <= 0)
                    ):
                        st.session_state["sidebar_preview_index"] = max(
                            0, current_preview_index - 1
                        )
                        st.rerun()

                with preview_col2:
                    st.write(f"**{current_preview_index + 1} / {total_files}**")

                with preview_col3:
                    if st.button(
                        "➡️",
                        key="sidebar_next",
                        disabled=(current_preview_index >= total_files - 1),
                    ):
                        st.session_state["sidebar_preview_index"] = min(
                            total_files - 1, current_preview_index + 1
                        )
                        st.rerun()

                # 进度条显示
                progress_value = (current_preview_index + 1) / total_files
                st.sidebar.progress(progress_value)

                # 图片选择滑块
                new_preview_index = st.sidebar.slider(
                    get_sidebar_label("select_preview_image"),
                    min_value=0,
                    max_value=total_files - 1,
                    value=current_preview_index,
                    key="sidebar_image_slider",
                )

                # 如果滑块值改变，更新索引
                if new_preview_index != current_preview_index:
                    st.session_state["sidebar_preview_index"] = new_preview_index
                    st.rerun()

                # 显示当前选中的图片
                uploaded_file = self.uploaded_file[current_preview_index]

                try:
                    # 处理当前选中的图片
                    if hasattr(uploaded_file, "read"):
                        uploaded_file.seek(0)
                        source_img = uploaded_file.read()
                        file_name = uploaded_file.name
                    else:
                        # 处理 LocalFileObj
                        with open(uploaded_file.name, "rb") as f:
                            source_img = f.read()
                        file_name = os.path.basename(uploaded_file.name)

                    file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                    image_ini = cv2.imdecode(file_bytes, 1)

                    if image_ini is None:
                        st.sidebar.error(
                            get_file_message("image_decode_error", filename=file_name)
                        )
                    else:
                        # 应用各种图像处理
                        if self.enable_pseudo_color and is_black_and_white(image_ini):
                            converted_image = convert_to_pseudo_colorizer(
                                image_ini,
                                contrast=self.image_contrast,
                                brightness=self.image_brightness,
                            )
                        else:
                            converted_image = image_ini.copy()

                        if self.enable_rotate_correction:
                            corrected_image = rotate_image(
                                converted_image,
                                angle_x=self.rot_angle_x,
                                angle_y=self.rot_angle_y,
                                zoom_factor=self.keystone_scale,
                            )
                        else:
                            corrected_image = converted_image.copy()

                        if self.enable_auto_keystone_correction:
                            corrected_image = auto_keystone_correction(
                                corrected_image, scale_factor=self.scale_factor_keystone
                            )
                        else:
                            corrected_image = corrected_image.copy()

                        if self.enable_background_fill:
                            corrected_image = fill_largest_polygon_white(
                                corrected_image, scale_factor=self.scale_factor_fill
                            )
                        else:
                            corrected_image = corrected_image.copy()

                        if self.image_enhancement_method == enhancement_options[1]:
                            corrected_image = enhance_texture(
                                corrected_image, method="clahe"
                            )
                        elif self.image_enhancement_method == enhancement_options[2]:
                            corrected_image = enhance_texture(
                                corrected_image, method="histogram_equalization"
                            )
                        else:
                            corrected_image = corrected_image.copy()

                        if (
                            self.undistortion_method == undistort_options[1]
                            and self.camera_matrix is not None
                            and self.dist_coeffs is not None
                        ):
                            distorted_image = camera_undistortion(
                                corrected_image, self.camera_matrix, self.dist_coeffs
                            )
                        elif self.undistortion_method == undistort_options[2]:
                            distorted_image = auto_undistort_image(
                                corrected_image, self.image_k1
                            )
                        else:
                            distorted_image = corrected_image.copy()

                        # 显示当前图片的处理前后对比
                        st.sidebar.image(
                            [image_ini, distorted_image],
                            caption=[
                                get_image_display_label('original_image', filename=file_name),
                                get_image_display_label('adjusted_image', filename=file_name),
                            ],
                            channels="BGR",
                        )

                        # 显示图片信息
                        st.sidebar.caption(get_image_display_label('file_name', filename=file_name))
                        st.sidebar.caption(
                            get_image_display_label('image_size', height=image_ini.shape[0], width=image_ini.shape[1])
                        )

                except Exception as e:
                    st.sidebar.error(
                        get_file_message("image_processing_error", filename=file_name, error=str(e))
                    )

            else:  # Handle single file upload
                source_img = self.uploaded_file.read()
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)

                if self.enable_pseudo_color and is_black_and_white(image_ini):
                    converted_image = convert_to_pseudo_colorizer(
                        image_ini,
                        contrast=self.image_contrast,
                        brightness=self.image_brightness,
                    )
                else:
                    converted_image = image_ini.copy()

                if self.enable_rotate_correction:
                    corrected_image = rotate_image(
                        converted_image,
                        angle_x=self.rot_angle_x,
                        angle_y=self.rot_angle_y,
                        zoom_factor=self.keystone_scale,
                    )
                else:
                    corrected_image = converted_image.copy()

                if self.enable_auto_keystone_correction:
                    corrected_image = auto_keystone_correction(
                        corrected_image, scale_factor=self.scale_factor_keystone
                    )
                else:
                    corrected_image = corrected_image.copy()

                if self.enable_background_fill:
                    corrected_image = fill_largest_polygon_white(
                        corrected_image, scale_factor=self.scale_factor_fill
                    )
                else:
                    corrected_image = corrected_image.copy()

                if self.image_enhancement_method == enhancement_options[1]:
                    corrected_image = enhance_texture(corrected_image, method="clahe")
                elif self.image_enhancement_method == enhancement_options[2]:
                    corrected_image = enhance_texture(
                        corrected_image, method="histogram_equalization"
                    )
                else:
                    corrected_image = corrected_image.copy()

                if (
                    self.undistortion_method == undistort_options[1]
                    and self.camera_matrix is not None
                    and self.dist_coeffs is not None
                ):
                    distorted_image = camera_undistortion(
                        corrected_image, self.camera_matrix, self.dist_coeffs
                    )
                elif self.undistortion_method == undistort_options[2]:
                    distorted_image = auto_undistort_image(
                        corrected_image, self.image_k1
                    )
                else:
                    distorted_image = corrected_image.copy()

                # Display original and distorted images
                st.sidebar.image(
                    [image_ini, distorted_image],
                    caption=[
                        get_image_display_label("original_image_caption", filename=self.uploaded_file.name),
                        get_image_display_label("adjusted_image_caption", filename=self.uploaded_file.name),
                    ],
                    channels="BGR",
                )
        else:
            st.sidebar.warning(get_sidebar_hint("upload_image_to_adjust_distortion"))

        st.sidebar.header(get_sidebar_header("output_file_path"))
        self.output_path = st.sidebar.text_input(
            get_sidebar_label("output_file_path"),
            value=abs_path("../output", path_type="current"),
            placeholder=get_sidebar_label("output_file_path_example")
        )

        if self.input_source in [input_options[4], input_options[5]]:
            st.sidebar.header(get_sidebar_header("rtsp_output_settings"))
            self.enable_rtsp_output = st.sidebar.checkbox(
                get_sidebar_label("enable_rtsp_output"), value=False
            )  # RTSP/RTMP输出地址输入
        if self.enable_rtsp_output:
            self.rtsp_output_url = st.sidebar.text_input(
                get_sidebar_label("rtsp_output_url"),
                placeholder=get_sidebar_label("rtsp_output_url_example"),
                help=get_sidebar_hint("rtsp_output_hint")
            )

        # 调用调试函数
        self.debug_detection_settings()

    def debug_detection_settings(self):
        """
        调试检测设置，显示当前配置信息
        """
        if self.from_streamlit:
            with st.sidebar.expander(get_main_label("debug_messages"), expanded=False):
                st.subheader(get_main_header("current_config"))
                st.write(
                    f"{get_main_label('config_label_model_type')}: {getattr(self, 'model_type', 'None')}"
                )
                st.write(
                    f"{get_main_label('config_label_image_type')}: {getattr(self, 'image_type', 'None')}"
                )
                st.write(
                    f"{get_main_label('config_label_rectangle_output')}: {getattr(self, 'rectangle_bounding_output', 'None')}"
                )
                st.write(
                    f"{get_main_label('config_label_conf_threshold')}: {getattr(self, 'conf_threshold', 'None')}"
                )
                st.write(
                    f"{get_main_label('config_label_iou_threshold')}: {getattr(self, 'iou_threshold', 'None')}"
                )

                st.subheader(get_main_header("class_settings"))
                st.write(
                    f"{get_main_label('config_label_available_classes')}: {getattr(self, 'available_classes', [])}"
                )
                st.write(
                    f"{get_main_label('config_label_selected_classes')}: {getattr(self, 'selected_classes', [])}"
                )

                if hasattr(self, "model") and hasattr(self.model, "names"):
                    # 处理不同类型的 model.names
                    if isinstance(self.model.names, dict):
                        model_classes = list(self.model.names.values())
                    elif isinstance(self.model.names, list):
                        model_classes = self.model.names
                    else:
                        model_classes = str(self.model.names)
                    st.write(
                        f"{get_main_label('config_label_model_classes')}: {model_classes}"
                    )

                if hasattr(self, "cls_name"):
                    st.write(f"{get_main_label('config_label_class_mapping')}: {self.cls_name}")

                # 显示实时检测信息
                if hasattr(self, "_debug_detected_classes"):
                    st.write(get_main_header("real_time_detection"))
                    st.write(
                        f"{get_main_label('config_label_detected_classes')}: {getattr(self, '_debug_detected_classes', [])}"
                    )
                    st.write(
                        f"{get_main_label('config_label_class_matches')}: {getattr(self, '_debug_class_matches', {})}"
                    )

                st.subheader(get_main_header("color_settings"))
                st.write(f"{get_main_label('config_label_color_list_length')}: {len(getattr(self, 'colors', []))}")
                if hasattr(self, "colors") and len(self.colors) > 0:
                    st.write(f"{get_main_label('config_label_first_colors')}: {self.colors[:3]}")

    def debug_display_state(self):
        """
        调试显示状态，输出当前图像和检测结果的状态信息
        """
        if self.from_streamlit:
            with st.expander(get_main_label("display_status_debug"), expanded=False):
                st.subheader(get_main_header("session_state_data"))
                st.write(
                    f"- saved_images_ini 数量: {len(st.session_state.get('saved_images_ini', []))}"
                )
                st.write(
                    f"- saved_images 数量: {len(st.session_state.get('saved_images', []))}"
                )
                st.write(
                    f"- saved_names 数量: {len(st.session_state.get('saved_names', []))}"
                )
                st.write(
                    f"- 当前图片索引: {st.session_state.get('image_play_index', 'None')}"
                )

                st.subheader(get_main_header("logtable_data"))
                if hasattr(self, "logTable"):
                    st.write(
                        f"- logTable.saved_images_ini 数量: {len(getattr(self.logTable, 'saved_images_ini', []))}"
                    )
                    st.write(
                        f"- logTable.saved_images 数量: {len(getattr(self.logTable, 'saved_images', []))}"
                    )
                    st.write(
                        f"- logTable.saved_names 数量: {len(getattr(self.logTable, 'saved_names', []))}"
                    )
                else:
                    st.write("- logTable: 未初始化")

                st.subheader(get_main_header("display_mode"))
                st.write(f"- 显示模式: {getattr(self, 'display_mode', 'None')}")
                st.write(
                    f"- 选择的目标: {st.session_state.get('multiselect_target', [])}"
                )

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
        elif hasattr(image_data, "read"):
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
                if hasattr(uploaded_file, "read"):
                    uploaded_file.seek(0)
                    source_img = uploaded_file.read()
                    file_name = uploaded_file.name
                else:
                    # 处理 LocalFileObj
                    with open(uploaded_file.name, "rb") as f:
                        source_img = f.read()
                    file_name = os.path.basename(uploaded_file.name)

                # 解码图片
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)

                if image_ini is None:
                    return {
                        "name": file_name,
                        "error": "无法解码图片",
                        "status": "error",
                    }

                # 应用图像处理
                processed_image = self.apply_image_processing(image_ini)

                # 进行检测
                framecopy = processed_image.copy()
                image, detInfo, select_info = self.frame_process(framecopy, file_name)

                # 保存结果
                save_chinese_image(self.output_path + "/image/" + file_name, image)

                return {
                    "name": file_name,
                    "original": image,
                    "processed": processed_image,
                    "status": "success",
                }
            except Exception as e:
                return {
                    "name": file_name if hasattr(uploaded_file, "name") else "unknown",
                    "error": str(e),
                    "status": "error",
                }

        # 使用线程池进行并行处理
        if len(uploaded_files) > 1:
            futures = [
                self.executor.submit(process_single_image, f) for f in uploaded_files
            ]
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e), "status": "timeout"})
            return results
        else:
            # 单个文件直接处理
            return [process_single_image(uploaded_files[0])]

    def apply_image_processing(self, image):
        """应用图像处理流水线"""
        processed = image.copy()
        undistort_options = get_sidebar_option("undistortion_methods")
        enhancement_options = get_sidebar_option("image_enhancement_methods")

        # 去畸变
        if hasattr(self, "undistortion_method"):
            if self.undistortion_method == undistort_options[1] and hasattr(
                self, "camera_matrix"
            ):
                if self.camera_matrix is not None and self.dist_coeffs is not None:
                    processed = camera_undistortion(
                        processed, self.camera_matrix, self.dist_coeffs
                    )
            elif self.undistortion_method == undistort_options[2] and hasattr(
                self, "image_k1"
            ):
                processed = auto_undistort_image(processed, self.image_k1)

        # 梯形校正
        if hasattr(self, "enable_rotate_correction") and self.enable_rotate_correction:
            processed = rotate_image(
                processed,
                angle_x=getattr(self, "rot_angle_x", 0),
                angle_y=getattr(self, "rot_angle_y", 0),
                zoom_factor=getattr(self, "keystone_scale", 1.0),
            )

        if (
            hasattr(self, "enable_auto_keystone_correction")
            and self.enable_auto_keystone_correction
        ):
            processed = auto_keystone_correction(
                processed, scale_factor=getattr(self, "scale_factor_keystone", 1.0)
            )

        if hasattr(self, "enable_background_fill") and self.enable_background_fill:
            processed = fill_largest_polygon_white(
                processed, scale_factor=getattr(self, "scale_factor_fill", 1.0)
            )

        # 图像增强
        if hasattr(self, "image_enhancement_method"):
            if self.image_enhancement_method == enhancement_options[1]:
                processed = enhance_texture(processed, method="clahe")
            elif self.image_enhancement_method == enhancement_options[2]:
                processed = enhance_texture(processed, method="histogram_equalization")

        # 伪彩色处理
        if hasattr(self, "enable_pseudo_color") and self.enable_pseudo_color:
            if is_black_and_white(processed):
                processed = convert_to_pseudo_colorizer(
                    processed,
                    contrast=getattr(self, "image_contrast", 1.0),
                    brightness=getattr(self, "image_brightness", 0),
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
        saved_images_ini = st.session_state.get("saved_images_ini", [])
        saved_images = st.session_state.get("saved_images", [])
        saved_results = getattr(self.logTable, "saved_results", [])
        saved_names = st.session_state.get("saved_names", [])

        # 如果session state为空但logTable有数据，同步数据
        if (
            not saved_images_ini
            and hasattr(self.logTable, "saved_images_ini")
            and self.logTable.saved_images_ini
        ):
            saved_images_ini = self.logTable.saved_images_ini
            saved_images = getattr(self.logTable, "saved_images", [])
            saved_names = getattr(self.logTable, "saved_names", [])
            # 同步到session state
            st.session_state["saved_images_ini"] = saved_images_ini
            st.session_state["saved_images"] = saved_images
            st.session_state["saved_names"] = saved_names

        if frame_id == -1:  # 显示所有目标
            if not saved_images_ini:
                st.warning(get_detection_message("no_detection_results"))
                if hasattr(self, "image_placeholder"):
                    self.image_placeholder.image(
                        load_default_image(),
                        caption=get_image_display_label("original_view"),
                    )
                if hasattr(self, "table_placeholder"):
                    self.table_placeholder.table(
                        pd.DataFrame(
                            columns=[
                                get_table_column("detection_result"),
                                get_table_column("type"),
                                get_table_column("location"),
                                get_table_column("area"),
                                get_table_column("time"),
                            ]
                        )
                    )
                return
            frame_id = 0  # 默认显示第一帧

        if frame_id >= len(saved_images_ini) or frame_id >= len(saved_results):
            st.warning(
                get_warning_message(
                    "frame_id_out_of_range_warning",
                    frame_id=frame_id,
                    total=len(saved_images_ini),
                )
            )
            return

        # 获取当前选中的目标过滤选项（多选）
        selected_targets = st.session_state.get(
            "multiselect_target", []
        )

        # 获取原始帧
        frame = saved_images_ini[frame_id]  # 获取指定帧的初始图像

        # 缓存图像调整大小的结果
        cache_key = f"frame_{frame_id}_{self.display_width}_{self.display_height}_{hash(tuple(selected_targets))}"
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
                        if (
                            selected_targets  # 如果有选中的目标
                            and chinese_name not in selected_targets  # 且当前目标不在选中列表中
                        ):
                            continue

                        # 确保 cls_id 在范围内
                        if cls_id < len(self.colors):
                            color = self.colors[cls_id]
                        else:
                            color = (255, 0, 0)  # 默认红色

                        # 确保矩形框绘制参数正确
                        info = {
                            "class_name": name,
                            "bbox": bbox,
                            "score": conf,
                            "class_id": cls_id,
                            "mask": None,
                        }
                        # 使用更明显的参数来绘制检测框
                        image, _ = draw_detections(
                            image,
                            info,
                            color=color,
                            alpha=0.3,  # 增加透明度使框更明显
                            line_number=cnt,
                            rectangle_bbox=getattr(
                                self, "rectangle_bounding_output", True
                            ),
                        )
                        cnt += 1

            # 缓存处理后的图像
            self.manage_cache_size(self.image_cache)
            self.image_cache[cache_key] = image.copy()

        # 现在不需要重复绘制检测框，因为已经在缓存逻辑中处理了

        # 调整图像大小
        if hasattr(self, "optimized_image_resize"):
            resized_image = self.optimized_image_resize(image, self.display_width, self.display_height)
            resized_frame = self.optimized_image_resize(frame, self.display_width, self.display_height)
        else:
            resized_image = cv2.resize(image, (self.display_width, self.display_height))
            resized_frame = cv2.resize(frame, (self.display_width, self.display_height))

        # 更新表格数据
        detection_results = (saved_results[frame_id] if frame_id < len(saved_results) else [])

        if detection_results:
            # 使用列表推导式提高性能
            filtered_results = [
                detInfo
                for detInfo in detection_results
                if isinstance(detInfo, list)
                and len(detInfo) == 6
                and (
                    not selected_targets  # 如果没有选中任何目标，显示所有目标
                    or detInfo[1] in selected_targets  # 否则只显示选中的目标
                )
            ]

            if filtered_results and hasattr(self, "table_placeholder"):
                disp_res = ResultLogger()
                for detInfo in filtered_results:
                    name, chinese_name, bbox, conf, use_time, cls_id = detInfo
                    disp_res.concat_results(
                        name, chinese_name, bbox, str(round(conf, 2)), str(use_time)
                    )
                self.table_placeholder.table(disp_res.results_df)
                self.update_category_counts(frame_id)
                if (
                    self.show_inclusion
                    and self.model_type == get_system_default("model_type_segmentation")
                ):
                    inclusion_df = compute_inclusion_relations(filtered_results)
                    if inclusion_df.empty:
                        inclusion_df = pd.DataFrame(columns=[get_table_column("string_id"), get_table_column("component_count")])
                    if hasattr(self, "inclusion_table_placeholder"):
                        self.inclusion_table_placeholder.table(inclusion_df)
                elif hasattr(self, "inclusion_table_placeholder"):
                    self.inclusion_table_placeholder.empty()
            else:
                if hasattr(self, "table_placeholder"):
                    self.table_placeholder.table(
                        pd.DataFrame(
                            columns=[
                                get_table_column("detection_result"),
                                get_table_column("type"),
                                get_table_column("location"),
                                get_table_column("area"),
                                get_table_column("time"),
                            ]
                        )
                    )
                self.update_category_counts(frame_id)
                if hasattr(self, "inclusion_table_placeholder"):
                    self.inclusion_table_placeholder.empty()
        else:
            if hasattr(self, "table_placeholder"):
                self.table_placeholder.table(
                    pd.DataFrame(
                        columns=[
                            get_table_column("detection_result"),
                            get_table_column("type"),
                            get_table_column("location"),
                            get_table_column("area"),
                            get_table_column("time"),
                        ]
                    )
                )
            self.update_category_counts(frame_id)
            if hasattr(self, "inclusion_table_placeholder"):
                self.inclusion_table_placeholder.empty()

        # 获取图像名称
        img_name = (
            saved_names[frame_id]
            if frame_id < len(saved_names)
            else f"Frame_{frame_id}"
        )

        # 根据显示模式显示处理后的图像或原始图像
        if hasattr(self, "display_mode") and hasattr(self, "image_placeholder"):
            display_modes = get_main_option("display_modes")
            if self.display_mode == display_modes[0]:
                self.image_placeholder.image(
                    resized_image,
                    channels="BGR",
                    caption=f"{get_image_display_label('detection_view')}: {img_name}",
                )
            else:  # display_modes[1]
                self.image_placeholder.image(
                    resized_frame,
                    channels="BGR",
                    caption=f"{get_image_display_label('original_view')}: {img_name}",
                )
                if hasattr(self, "image_placeholder_res"):
                    self.image_placeholder_res.image(
                        resized_image,
                        channels="BGR",
                        caption=f"{get_image_display_label('detection_view')}: {img_name}",
                    )

        # 更新GPS信息显示
        if all(
            getattr(self, name, None) is not None
            for name in [
                "gps_lat_placeholder",
                "gps_lon_placeholder",
                "gps_alt_placeholder",
                "gps_time_placeholder",
            ]
        ):
            lat = lon = alt = gps_time = "--"
            if getattr(self, "enable_gps_parsing", False):
                if frame_id < len(getattr(self.logTable, "saved_image_paths", [])):
                    img_path = self.logTable.saved_image_paths[frame_id]
                    if img_path and os.path.exists(img_path):
                        gps = extract_gps_info(img_path)
                        if gps:
                            if "latitude" in gps:
                                lat = f"{gps['latitude']:.6f}°"
                                if 'latitude_ref' in gps:
                                    lat += f" {gps['latitude_ref']}"
                            if "longitude" in gps:
                                lon = f"{gps['longitude']:.6f}°"
                                if 'longitude_ref' in gps:
                                    lon += f" {gps['longitude_ref']}"
                            if "altitude" in gps:
                                alt = f"{gps['altitude']:.1f}m"
                                if gps.get('altitude_ref') == 1:
                                    alt += " (" + get_metric_label("below_sea_level") + ")"
                                else:
                                    alt += " (" + get_metric_label("above_sea_level") + ")"
                            if "gps_timestamp" in gps and "gps_datestamp" in gps:
                                ts = gps["gps_timestamp"]
                                if isinstance(ts, tuple) and len(ts) == 3:
                                    ts = f"{int(ts[0]):02d}:{int(ts[1]):02d}:{int(ts[2]):02d}"
                                gps_time = f"{gps['gps_datestamp']} {ts}"

            self.gps_lat_placeholder.metric(get_metric_label("gps_latitude"), lat)
            self.gps_lon_placeholder.metric(get_metric_label("gps_longitude"), lon)
            self.gps_alt_placeholder.metric(get_metric_label("gps_altitude"), alt)
            self.gps_time_placeholder.metric(get_metric_label("gps_time"), gps_time)

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
        params = {"conf": self.conf_threshold, "iou": self.iou_threshold}
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

            # 只对包含string类型的检测结果进行缺失面板和错位面板检测
            if (
                self.show_missing_panel
                and self.model_type == get_system_default("model_type_segmentation")
            ):
                # 检查是否有string类型的检测结果
                has_string = any(info.get("class_name") == "string" for info in det_info)
                if has_string:
                    det_info.extend(compute_missing_panels(det_info, image.shape))

            if (
                self.show_misaligned_panel
                and self.model_type == get_system_default("model_type_segmentation")
            ):
                # 检查是否有string类型的检测结果
                has_string = any(info.get("class_name") == "string" for info in det_info)
                if has_string:
                    det_info.extend(compute_misaligned_panels(det_info))
            if len(det_info):
                disp_res = ResultLogger()
                res = None
                cnt = 0

                # 初始化调试信息存储
                self._debug_detected_classes = []
                self._debug_class_matches = {}

                # 遍历检测到的对象
                for idx, info in enumerate(det_info):
                    name, bbox, conf, cls_id, mask = (
                        info["class_name"],
                        info["bbox"],
                        info["score"],
                        info["class_id"],
                        info["mask"],
                    )

                    # 收集调试信息（不直接显示）
                    if idx == 0:  # 只在第一个检测对象时收集，避免重复
                        self._debug_detected_classes = [
                            info["class_name"] for info in det_info
                        ]
                        for det_info_item in det_info:
                            det_name = det_info_item["class_name"]
                            self._debug_class_matches[det_name] = (
                                det_name in self.selected_classes
                            )

                    # Ensure cls_id is within bounds
                    if name == "missing_panel":
                        color = Segmentation_class_colors.get("missing_panel", (255, 0, 255))
                        draw_flag = self.show_missing_panel
                        chinese_name = "光伏板缺失"
                    elif name == "misaligned_panel":
                        color = Segmentation_class_colors.get("misaligned_panel", (255, 165, 0))
                        draw_flag = self.show_misaligned_panel
                        chinese_name = "光伏板移位"
                    else:
                        if cls_id >= len(self.colors):
                            st.warning(
                                get_warning_message(
                                    "index_out_of_range_warning", cls_id=cls_id
                                )
                            )
                            color = (255, 0, 0)  # 默认红色
                        else:
                            color = self.colors[cls_id]
                        chinese_name = self.cls_name.get(name, "未知类别")
                        draw_flag = name in self.selected_classes

                    # 确保类别匹配逻辑正确
                    if draw_flag:
                        # 绘制检测框、标签和面积信息
                        if not is_api:
                            image, aim_frame_area = draw_detections(
                                image,
                                info,
                                color=color,
                                alpha=0.5,
                                line_number=cnt,
                                rectangle_bbox=self.rectangle_bounding_output,
                            )
                        else:
                            image, aim_frame_area = draw_detections(
                                image,
                                info,
                                alpha=0.5,
                                line_number=cnt,
                                is_api=True,
                                rectangle_bbox=self.rectangle_bounding_output,
                            )

                        res = disp_res.concat_results(
                            name,
                            chinese_name,
                            bbox,
                            str(int(aim_frame_area)),
                            (
                                video_time
                                if video_time is not None
                                else str(round(use_time, 2))
                            ),
                        )

                        # 添加日志条目
                        self.logTable.add_log_entry(
                            file_name,
                            name,
                            chinese_name,
                            bbox,
                            int(aim_frame_area),
                            (
                                video_time
                                if video_time is not None
                                else str(round(use_time, 2))
                            ),
                        )
                        # 记录检测信息
                        detInfo.append(
                            [
                                name,
                                chinese_name,
                                bbox,
                                int(aim_frame_area),
                                (
                                    video_time
                                    if video_time is not None
                                    else str(round(use_time, 2))
                                ),
                                cls_id,
                            ]
                        )

                        # 添加到选择信息列表，避免重复
                        if chinese_name not in select_info:
                            select_info.append(chinese_name)
                        cnt += 1

                # 在表格中显示检测结果
                if not is_api:
                    self.table_placeholder.table(res)
                    # 注意：类别统计会在 toggle_comboBox 中更新，这里不需要重复更新

        if not select_info:
            select_info = ["全部目标"]
        st.session_state["select_info"] = select_info
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
        # 注意：这里是演示模式，不需要更新类别统计
        # 添加适当的延迟
        cv2.waitKey(1)

    def update_category_counts(self, current_frame_id=None):
        """更新并显示类别计数表格"""
        # 添加安全检查，确保占位符存在
        if not hasattr(self, "current_image_category_placeholder") or self.current_image_category_placeholder is None:
            return
        if not hasattr(self, "total_category_placeholder") or self.total_category_placeholder is None:
            return

        # 获取当前图片的类别统计
        if current_frame_id is not None:
            self.update_current_image_category_counts(current_frame_id)

        # 获取总体类别统计
        self.update_total_category_counts()

    def update_current_image_category_counts(self, frame_id):
        """更新当前图片的类别统计"""
        try:
            # 获取当前图片的检测结果
            saved_results = getattr(self.logTable, "saved_results", [])
            saved_names = st.session_state.get("saved_names", [])

            if frame_id >= len(saved_results) or not saved_results[frame_id]:
                # 如果没有检测结果，显示空表格
                empty_df = pd.DataFrame(columns=[get_table_column("category"), get_table_column("count")])
                self.current_image_category_placeholder.table(empty_df)
                return

            # 获取当前图片名称
            img_name = saved_names[frame_id] if frame_id < len(saved_names) else f"图片_{frame_id + 1}"

            # 统计当前图片的类别
            current_results = saved_results[frame_id]
            category_counts = {}

            for detInfo in current_results:
                if isinstance(detInfo, list) and len(detInfo) >= 2:
                    category = detInfo[1]  # 类别名称在索引1
                    if category in category_counts:
                        category_counts[category] += 1
                    else:
                        category_counts[category] = 1

            # 转换为DataFrame
            if category_counts:
                current_counts = pd.DataFrame(list(category_counts.items()), columns=[get_table_column("category"), get_table_column("count")])
                current_counts = current_counts.sort_values(get_table_column("count"), ascending=False)
            else:
                current_counts = pd.DataFrame(columns=[get_table_column("category"), get_table_column("count")])

            # 添加表格标题信息
            if not current_counts.empty:
                self.current_image_category_placeholder.write(f"📊 **{img_name}** 中检测到的目标:")
                self.current_image_category_placeholder.table(current_counts)
            else:
                self.current_image_category_placeholder.write(f"📊 **{img_name}** 中未检测到目标")
                self.current_image_category_placeholder.table(pd.DataFrame(columns=[get_table_column("category"), get_table_column("count")]))

        except Exception as e:
            st.error(f"更新当前图片类别统计时出错: {str(e)}")
            self.current_image_category_placeholder.table(pd.DataFrame(columns=[get_table_column("category"), get_table_column("count")]))

    def update_total_category_counts(self):
        """更新总体类别统计，包含图片来源信息"""
        try:
            saved_results = getattr(self.logTable, "saved_results", [])
            saved_names = st.session_state.get("saved_names", [])

            if not saved_results:
                # 如果没有检测结果，显示空表格
                empty_df = pd.DataFrame(columns=[get_table_column("category"), get_table_column("total_count"), get_table_column("distribution_images")])
                self.total_category_placeholder.table(empty_df)
                return

            # 统计每个类别在各图片中的分布
            category_distribution = {}

            for frame_id, results in enumerate(saved_results):
                img_name = saved_names[frame_id] if frame_id < len(saved_names) else f"{get_detection_message("image_default_name").format(idx=frame_id + 1)}"

                if results:
                    frame_categories = {}
                    for detInfo in results:
                        if isinstance(detInfo, list) and len(detInfo) >= 2:
                            category = detInfo[1]  # 类别名称在索引1
                            if category in frame_categories:
                                frame_categories[category] += 1
                            else:
                                frame_categories[category] = 1

                    # 记录每个类别在当前图片中的分布
                    for category, count in frame_categories.items():
                        if category not in category_distribution:
                            category_distribution[category] = []
                        category_distribution[category].append(f"{img_name}({count})")

            # 转换为DataFrame
            if category_distribution:
                total_data = []
                for category, distribution in category_distribution.items():
                    total_count = sum(int(item.split('(')[1].split(')')[0]) for item in distribution)
                    distribution_str = ", ".join(distribution)
                    total_data.append([category, total_count, distribution_str])

                total_counts = pd.DataFrame(total_data, columns=[get_table_column("category"), get_table_column("total_count"), get_table_column("distribution_images")])
                total_counts = total_counts.sort_values(get_table_column("total_count"), ascending=False)

                self.total_category_placeholder.write(f"📈 **总体统计** (共{len(saved_results)}张图片):")
                self.total_category_placeholder.table(total_counts)
            else:
                self.total_category_placeholder.write("📈 **总体统计**: 暂无检测结果")
                self.total_category_placeholder.table(pd.DataFrame(columns=[get_table_column("category"), get_table_column("total_count"), get_table_column("distribution_images")]))

        except Exception as e:
            st.error(f"更新总体类别统计时出错: {str(e)}")
            self.total_category_placeholder.table(pd.DataFrame(columns=[get_table_column("category"), get_table_column("total_count"), get_table_column("distribution_images")]))

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
            unsafe_allow_html=True,
        )

        # st.title(self.title) # 显示系统标题
        st.write(get_system_info("separator"))
        st.write(get_system_info("description"))
        st.write(get_system_info("separator"))

        # 插入一条分割线

        # 创建列布局，将表格移到最右侧
        col1, col2 = st.columns([1, 1])

        # 在第一列设置显示模式的选择
        with col1:
            st.subheader(get_main_header("video_image_detection_system"))
            self.display_mode = st.radio(
                get_main_label("display_mode_selection"),
                get_main_option("display_modes"),
            )
            self.image_placeholder = st.empty()
            self.image_placeholder_res = st.empty()
            # 根据显示模式创建用于显示视频画面的空容器，优化默认图像显示逻辑，避免覆盖检测结果
            display_modes = get_main_option("display_modes")
            if self.display_mode == display_modes[0]:
                # 只在没有任何保存图像且没有session state中的图像时显示默认图像
                if (
                    not hasattr(self.logTable, "saved_images_ini")
                    or not self.logTable.saved_images_ini
                ) and (not st.session_state.get("saved_images_ini")):
                    self.image_placeholder.image(
                        load_default_image(),
                        caption=get_image_display_label("original_view"),
                    )
            else:
                # "双画面显示"
                if (
                    not hasattr(self.logTable, "saved_images_ini")
                    or not self.logTable.saved_images_ini
                ) and (not st.session_state.get("saved_images_ini")):
                    self.image_placeholder.image(
                        load_default_image(),
                        caption=get_image_display_label("original_view"),
                    )
                    self.image_placeholder_res.image(
                        load_default_image(),
                        caption=get_image_display_label("detection_view"),
                    )
            # 显示用的进度条
            self.progress_bar = st.progress(0)

        # 创建一个空的结果表格
        res = concat_results("None", "[0, 0, 0, 0]", "0.00", "0.00s")

        # 在最右侧列设置识别结果表格的显示
        with col2:
            st.subheader(get_main_header("current_image_results"))
            self.table_placeholder = st.empty()  # 调整到最右侧显示
            self.table_placeholder.table(res)

            # 在当前图片检测结果下方添加当前图片类别统计
            st.subheader(get_main_header("current_category_statistics"))
            self.current_image_category_placeholder = st.empty()

            st.subheader(get_main_header("inclusion_relationship"))
            self.inclusion_table_placeholder = st.empty()

            # 目标过滤选项（针对当前图片）
            st.subheader(get_main_label("target_filter"))
            self.selectbox_placeholder = st.empty()

            # 初始化目标过滤选项 - 根据当前图片动态获取检测目标
            idx = st.session_state.get("image_play_index", 0)

            # 获取当前图片的检测目标（优先从session_state获取，然后从logTable获取）
            saved_targets_info = st.session_state.get("saved_targets_info", [])
            if not saved_targets_info and hasattr(self.logTable, "saved_targets_info"):
                saved_targets_info = self.logTable.saved_targets_info
                # 同步到session_state
                st.session_state["saved_targets_info"] = saved_targets_info

            if saved_targets_info and idx < len(saved_targets_info):
                detected_targets = saved_targets_info[idx]
            else:
                detected_targets = st.session_state.get("select_info", [get_system_default("target_all")])

            # 从检测目标列表中移除"全部目标"，只保留实际的类别名称
            available_targets = [target for target in detected_targets if target != get_system_default("target_all")]

            # multiselect动态key，确保当目标列表变化时multiselect会刷新
            multiselect_key = f"multiselect_target_{idx}_{hash(tuple(available_targets))}"

            # 确保当前选中的目标在新的目标列表中，默认选择所有可用目标
            current_selected = st.session_state.get("multiselect_target", available_targets.copy())
            # 过滤掉不在当前目标列表中的选项
            current_selected = [target for target in current_selected if target in available_targets]

            # 自动添加新出现的检测类别（如"光伏板缺失"、"光伏板移位"）
            for target in available_targets:
                if target not in current_selected and target in [get_class_name("missing_panel"), get_class_name("misaligned_panel")]:
                    current_selected.append(target)

            # 如果没有选中任何目标，默认选择所有目标
            if not current_selected:
                current_selected = available_targets.copy()

            # 添加快捷操作按钮
            if available_targets:
                col_select_all, col_select_none = st.columns(2)
                with col_select_all:
                    if st.button(get_button_text("select_all"), key=f"select_all_{idx}"):
                        st.session_state["multiselect_target"] = available_targets.copy()
                        st.rerun()
                with col_select_none:
                    if st.button(get_button_text("deselect_all"), key=f"select_none_{idx}"):
                        st.session_state["multiselect_target"] = []
                        st.rerun()

            selected_targets = self.selectbox_placeholder.multiselect(
                get_main_label("target_filter"),
                available_targets,
                default=current_selected,
                key=multiselect_key,
            )

            # 只在选项变化时同步并刷新显示
            if (
                "last_selected_targets" not in st.session_state
                or st.session_state["last_selected_targets"] != selected_targets
            ):
                self.selected_targets = selected_targets
                st.session_state["multiselect_target"] = selected_targets
                st.session_state["last_selected_targets"] = selected_targets
                self.toggle_comboBox(idx)

        # 图片浏览控制（移动到总体类别统计上方）
        st.markdown("---")

        # 显示批量处理汇总信息（如果存在）
        if st.session_state.get("batch_processing_summary"):
            st.success(st.session_state["batch_processing_summary"])

        st.subheader(get_main_header("image_browser_control"))

        # 检查是否有检测结果（优先检查session state，然后检查logTable）
        saved_images_ini = st.session_state.get("saved_images_ini", [])
        if not saved_images_ini and hasattr(self.logTable, "saved_images_ini"):
            saved_images_ini = self.logTable.saved_images_ini
            # 同步到session state
            st.session_state["saved_images_ini"] = saved_images_ini
            st.session_state["saved_images"] = getattr(self.logTable, "saved_images", [])
            st.session_state["saved_names"] = getattr(self.logTable, "saved_names", [])

        if len(saved_images_ini) > 0:
            total_imgs = len(saved_images_ini)
            st.info(get_statistic_message("total_images_info", count=total_imgs))

            # 初始化或验证图片索引
            if "image_play_index" not in st.session_state:
                st.session_state["image_play_index"] = 0
            elif st.session_state["image_play_index"] >= total_imgs:
                st.session_state["image_play_index"] = total_imgs - 1

            current_index = st.session_state["image_play_index"]

            # 创建三列布局：[上一张] [当前信息] [下一张]
            col_prev, col_info, col_next = st.columns([1, 2, 1])

            with col_prev:
                if st.button(
                    get_button_text("previous_image"),
                    key="prev_btn",
                    disabled=(current_index <= 0),
                ):
                    st.session_state["image_play_index"] = max(0, current_index - 1)
                    st.rerun()

            with col_info:
                st.write(get_statistic_message("image_index_info", current=current_index + 1, total=total_imgs))
                # 显示当前图片名称
                if current_index < len(st.session_state.get("saved_names", [])):
                    img_name = st.session_state["saved_names"][current_index]
                    st.caption(get_statistic_message("filename_info", filename=img_name))

            with col_next:
                if st.button(
                    get_button_text("next_image"),
                    key="next_btn",
                    disabled=(current_index >= total_imgs - 1),
                ):
                    st.session_state["image_play_index"] = min(total_imgs - 1, current_index + 1)
                    st.rerun()

            # 添加滑块控制
            new_index = st.slider(
                get_main_label("image_slider_label"),
                min_value=0,
                max_value=total_imgs - 1,
                value=current_index,
                key="image_slider",
            )

            # 如果滑块值改变，更新索引
            if new_index != current_index:
                st.session_state["image_play_index"] = new_index
                st.rerun()

        else:
            st.info(get_detection_message("no_detection_results"))
            # 显示默认图像
            if hasattr(self, "image_placeholder"):
                self.image_placeholder.image(load_default_image(), caption=get_image_display_label("original_view"))
                if self.display_mode == display_modes[1] and hasattr(
                    self, "image_placeholder_res"
                ):
                    self.image_placeholder_res.image(load_default_image(), caption=get_image_display_label("detection_view"))

        # 在创建占位符后再调用update_category_counts
        st.subheader(get_main_header("total_category_statistics"))

        # 总体类别统计
        self.total_category_placeholder = st.empty()

        # 初始化类别统计（使用当前图片索引）
        current_idx = st.session_state.get("image_play_index", 0)
        self.update_category_counts(current_idx)

        # 创建一个导出结果的按钮
        st.write("---------------------")
        if st.button(get_button_text("export_results"), key="main_export_results"):
            current_time = datetime.now().strftime("%Y年%m月%d日_%H时%M分")

            # 使用新的命名配置生成文件名
            base_filename = generate_filename(
                "report",
                image_type=self.image_type,
                task_type=self.model_type,
                timestamp=current_time,
            )
            self.saved_log_data = os.path.join(self.csv_output_path, base_filename)

            if self.export_format == "CSV":
                self.saved_log_data += ".csv"
                self.logTable.save_to_csv(self.saved_log_data)
                st.success(
                    get_export_message(
                        "export_success",
                        file_type="CSV数据表",
                        filename=os.path.basename(self.saved_log_data),
                    )
                )
            elif self.export_format == "Excel":
                self.saved_log_data += ".xlsx"
                self.logTable.save_to_excel(self.saved_log_data)
                st.success(
                    get_export_message(
                        "export_success",
                        file_type="Excel电子表格",
                        filename=os.path.basename(self.saved_log_data),
                    )
                )
            elif self.export_format == "JSON":
                self.saved_log_data += ".json"
                self.logTable.save_to_json(self.saved_log_data)
                st.success(
                    get_export_message(
                        "export_success",
                        file_type="JSON数据文件",
                        filename=os.path.basename(self.saved_log_data),
                    )
                )
            elif self.export_format == "Word":
                self.saved_log_data += ".docx"
                # 构建检测参数字典
                detection_params = {
                    "model_type": self.model_type,
                    "image_type": self.image_type,
                    "conf_threshold": self.conf_threshold,
                    "iou_threshold": self.iou_threshold,
                    "selected_classes": getattr(self, "selected_classes", []),
                    "cls_name": getattr(self, "cls_name", {}),
                    "enable_gps_parsing": getattr(self, "enable_gps_parsing", False),
                }
                self.logTable.save_to_word(self.saved_log_data, detection_params)
                st.success(
                    get_export_message(
                        "export_success",
                        file_type="Word检测报告",
                        filename=os.path.basename(self.saved_log_data),
                    )
                )

            # 根据用户设置决定是否清空检测结果
            if self.clear_after_export:
                self.logTable.clear_data()
                st.info("检测结果已清空")
        st.subheader(get_main_header("history_log"))
        # 显示所有结果记录的空白表格
        self.log_table_placeholder = st.empty()
        self.logTable.update_table(self.log_table_placeholder)

        # 在第五列设置一个空的停止按钮占位符

        with col1:
            st.write("")
            run_button = st.button(get_button_text("start_detection"), key="main_start_detection")
            self.close_placeholder = st.empty()

        st.subheader(get_main_header("realtime_dashboard"))
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
        self.frame_count_placeholder.metric(
            get_metric_label("current_frame"), st.session_state["current_frame_count"]
        )
        self.fps_placeholder.metric(
            get_metric_label("current_fps"), st.session_state["current_fps"]
        )
        self.target_count_placeholder.metric(
            get_metric_label("target_count"), st.session_state["current_target_count"]
        )
        self.detection_time_placeholder.metric(
            get_metric_label("detection_time"),
            st.session_state["current_detection_time"],
        )

        st.subheader(get_main_header("gps_info"))
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            self.gps_lat_placeholder = st.empty()
        with g2:
            self.gps_lon_placeholder = st.empty()
        with g3:
            self.gps_alt_placeholder = st.empty()
        with g4:
            self.gps_time_placeholder = st.empty()

        self.gps_lat_placeholder.metric(get_metric_label("gps_latitude"), "--")
        self.gps_lon_placeholder.metric(get_metric_label("gps_longitude"), "--")
        self.gps_alt_placeholder.metric(get_metric_label("gps_altitude"), "--")
        self.gps_time_placeholder.metric(get_metric_label("gps_time"), "--")

        # 初始化完成后显示检测结果
        self.toggle_comboBox(st.session_state.get("image_play_index", 0))

        # 添加调试信息
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

            input_source_mode = get_sidebar_option("input_sources")
            if self.input_source == input_source_mode[0] or self.input_source == input_source_mode[1]:
                if self.uploaded_file:
                    self._process_image_input()
                else:
                    st.warning(get_file_message("upload_files_first"))

            elif self.input_source == input_source_mode[2] or self.input_source == input_source_mode[3]:
                if hasattr(self, "uploaded_video") and self.uploaded_video:
                    self._process_video_input()
                else:
                    st.warning(get_file_message("upload_video_first"))

            elif self.input_source == input_source_mode[4]:
                if self.selected_camera is not None:
                    camera_id = (
                        int(self.selected_camera.split(":")[0])
                        if ":" in str(self.selected_camera)
                        else int(self.selected_camera)
                    )
                    self._process_camera_input(camera_id)
                else:
                    st.warning(get_camera_message("select_camera_first"))

            elif self.input_source == input_source_mode[5]:
                if self.rtsp_input_url:
                    self._process_rtsp_input(self.rtsp_input_url)
                else:
                    st.warning(get_rtsp_message("input_rtsp_first"))

            else:
                st.error(get_warning_message("unsupported_input_source", source=self.input_source))

        except Exception as e:
            st.error(get_warning_message("input_processing_error", error=str(e)))

    def _ensure_initialization(self):
        """
        确保所有必需的属性都已正确初始化
        """
        # 确保 logTable 存在
        if not hasattr(self, "logTable") or self.logTable is None:
            if hasattr(st, "session_state") and "logTable" in st.session_state:
                self.logTable = st.session_state["logTable"]
            else:
                # 如果 saved_log_data 不存在，创建一个默认的
                if not hasattr(self, "saved_log_data"):
                    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.saved_log_data = os.path.join(
                        getattr(
                            self,
                            "csv_output_path",
                            abs_path("../output/logs/", path_type="current"),
                        ),
                        f"log_table_data_{current_time}.csv",
                    )

                self.logTable = LogTable(self.saved_log_data)
                if hasattr(st, "session_state"):
                    st.session_state["logTable"] = self.logTable

        # 确保 progress_bar 存在
        if not hasattr(self, "progress_bar") or self.progress_bar is None:
            self.progress_bar = st.progress(0)

        # 确保 close_placeholder 存在
        if not hasattr(self, "close_placeholder") or self.close_placeholder is None:
            self.close_placeholder = st.empty()

        # 确保显示相关属性存在
        if not hasattr(self, "display_width"):
            self.display_width = 640
        if not hasattr(self, "display_height"):
            self.display_height = 480

    def _process_image_input(self):
        """
        处理图片输入
        """
        if not self.uploaded_file:
            st.warning(get_sidebar_hint("upload_files_first"))
            return

        self.logTable.clear_frames()
        display_modes = get_main_option("display_modes")

        # 初始化进度显示
        progress_container = st.container()
        with progress_container:
            st.info(get_detection_message("image_detection_start"))
            overall_progress = st.progress(0)
            status_text = st.empty()
            current_image_info = st.empty()

        if isinstance(self.uploaded_file, list):
            # 批量处理多张图片
            total_files = len(self.uploaded_file)
            status_text.write(get_file_message("processing_files", count=total_files))

            # 计算预估时间
            estimated_time_per_image = 2.0  # 假设每张图片需要2秒
            estimated_total_time = total_files * estimated_time_per_image
            status_text.write(get_file_message("estimated_time", time=estimated_total_time))

            start_time = time.time()
            successful_count = 0
            failed_count = 0

            for idx, uploaded_file in enumerate(self.uploaded_file):
                try:
                    # 更新当前处理信息
                    current_file_name = (
                        uploaded_file.name
                        if hasattr(uploaded_file, "name")
                        else f"{get_detection_message("image_default_name", idx=idx + 1)}"
                    )
                    current_image_info.info(
                        get_detection_message(
                            "processing_current",
                            filename=current_file_name,
                            current=idx + 1,
                            total=total_files,
                        )
                    )

                    # 读取图片数据和获取路径
                    img_path = None
                    if hasattr(uploaded_file, "read"):
                        # 这是通过文件上传器上传的文件
                        uploaded_file.seek(0)
                        source_img = uploaded_file.read()
                        file_name = uploaded_file.name

                        # 为上传的文件创建临时文件以获取完整路径
                        if getattr(self, "enable_gps_parsing", False):
                            # 创建临时文件保存图片，以便GPS解析
                            temp_dir = tempfile.mkdtemp()
                            temp_file_path = os.path.join(temp_dir, file_name)
                            with open(temp_file_path, 'wb') as temp_file:
                                temp_file.write(source_img)
                            img_path = temp_file_path
                    else:
                        # 这是LocalFileObj，name包含完整路径
                        with open(uploaded_file.name, "rb") as f:
                            source_img = f.read()
                        file_name = os.path.basename(uploaded_file.name)
                        img_path = uploaded_file.name  # 完整路径

                    # 解码图片
                    file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                    image_ini = cv2.imdecode(file_bytes, 1)

                    if image_ini is None:
                        st.error(get_file_message("image_decode_error", filename=file_name))
                        failed_count += 1
                        continue

                    # 应用图像处理
                    processed_image = self.apply_image_processing(image_ini)

                    # 进行检测
                    framecopy = processed_image.copy()
                    image, detInfo, select_info = self.frame_process(framecopy, file_name)

                    # 保存结果
                    save_chinese_image(self.output_path + "/image/" + file_name, image)

                    # 更新状态
                    st.session_state["current_frame_count"] = idx + 1
                    st.session_state["current_target_count"] = len(detInfo)
                    st.session_state["current_detection_time"] = self.detection_time

                    # 更新显示
                    self.frame_count_placeholder.metric(get_main_label("current_frame"), idx + 1)
                    self.target_count_placeholder.metric(get_main_label("target_count"), len(detInfo))
                    self.detection_time_placeholder.metric(get_main_label("detection_time"), self.detection_time)

                    # 显示图片
                    resized_image = cv2.resize(image, (self.display_width, self.display_height))
                    resized_frame = cv2.resize(processed_image, (self.display_width, self.display_height))

                    if self.display_mode == display_modes[0]:
                        self.image_placeholder.image(
                            resized_image,
                            channels="BGR",
                            caption=f"{get_image_display_label('detection_view')}: {file_name}",
                        )
                    else:
                        self.image_placeholder.image(
                            resized_frame,
                            channels="BGR",
                            caption=f"{get_image_display_label('original_view')}: {file_name}",
                        )
                        if hasattr(self, "image_placeholder_res"):
                            self.image_placeholder_res.image(
                                resized_image,
                                channels="BGR",
                                caption=f"{get_image_display_label('detection_view')}: {file_name}",
                            )

                    # 添加到日志表（现在img_path不为None）
                    self.logTable.add_frames(image, detInfo, processed_image, file_name, img_path)

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
                        status_text.success(
                            get_detection_message(
                                "batch_processing_progress",
                                current=idx + 1,
                                total=total_files,
                                remaining_time=round(remaining_time, 2),
                            )
                        )

                    # 添加短暂延迟以显示进度
                    time.sleep(0.1)

                except Exception as e:
                    st.error(
                        get_file_message(
                            "image_processing_error",
                            filename=current_file_name,
                            error=str(e),
                        )
                    )
                    failed_count += 1
                    continue

            # 完成后的总结
            total_time = time.time() - start_time

            # 在终端输出完成信息
            print("🎉 批量检测完成！")
            print(f"   - 总文件数: {total_files}")
            print(f"   - 成功处理: {successful_count}张")
            print(f"   - 失败处理: {failed_count}张")
            print(f"   - 总耗时: {total_time:.2f}秒")
            print(f"   - 平均耗时: {total_time / total_files:.2f}秒/张")

            if failed_count > 0:
                print(f"⚠️  有{failed_count}张图片处理失败，请检查上述错误信息")

            # 生成汇总信息用于界面显示
            summary_msg = get_detection_message(
                "batch_processing_summary",
                successful_count=successful_count,
                failed_count=failed_count,
                total_time=total_time,
            )

            # 仅在处理过程中显示完成消息，不保存到session_state
            current_image_info.success(get_detection_message("batch_processing_complete"))
            status_text.success(summary_msg)

            # 保存总结信息到 session_state，便于在"图片浏览控制"上方显示
            st.session_state["batch_processing_summary"] = summary_msg
            overall_progress.progress(1.0)

            # 立即更新session state以确保UI同步
            st.session_state["saved_images_ini"] = self.logTable.saved_images_ini.copy()
            st.session_state["saved_images"] = self.logTable.saved_images.copy()
            st.session_state["saved_names"] = self.logTable.saved_names.copy()
            # 同步每张图片的目标信息
            if hasattr(self.logTable, "saved_targets_info"):
                st.session_state["saved_targets_info"] = self.logTable.saved_targets_info.copy()

            # 确保索引重置为0以显示第一张图片
            st.session_state["image_play_index"] = 0

            # 更新历史日志显示
            if hasattr(self, "log_table_placeholder"):
                self.logTable.update_table(self.log_table_placeholder)

            # 立即刷新页面，让selectbox自动更新
            st.rerun()

        else:
            # 单张图片处理
            try:
                # 显示处理状态
                progress_container = st.container()
                with progress_container:
                    st.info(get_file_message("single_image_processing_start"))
                    single_progress = st.progress(0)
                    status_info = st.empty()

                status_info.write(get_file_message("reading_image_file"))
                single_progress.progress(0.2)

                source_img = self.uploaded_file.read()
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)

                if image_ini is None:
                    st.error(get_file_message("image_decode_failed"))
                    return

                # 为单张上传的图片创建临时文件
                img_path = None
                if getattr(self, "enable_gps_parsing", False):
                    temp_dir = tempfile.mkdtemp()
                    temp_file_path = os.path.join(temp_dir, self.uploaded_file.name)
                    with open(temp_file_path, 'wb') as temp_file:
                        temp_file.write(source_img)
                    img_path = temp_file_path

                status_info.write(get_file_message("applying_image_processing"))
                single_progress.progress(0.4)

                # 应用图像处理
                processed_image = self.apply_image_processing(image_ini)

                status_info.write(get_general_message("ai_detection_running"))
                single_progress.progress(0.6)

                # 进行检测
                framecopy = processed_image.copy()
                image, detInfo, select_info = self.frame_process(framecopy, self.uploaded_file.name)

                status_info.write(get_file_message("saving_detection_results"))
                single_progress.progress(0.8)

                # 保存结果
                save_chinese_image(self.output_path + "/image/" + self.uploaded_file.name, image)

                # 更新状态
                st.session_state["current_frame_count"] = 1
                st.session_state["current_target_count"] = len(detInfo)
                st.session_state["current_detection_time"] = self.detection_time

                # 更新显示
                self.frame_count_placeholder.metric(get_main_label("current_frame"), 1)
                self.target_count_placeholder.metric(get_main_label("target_count"), len(detInfo))
                self.detection_time_placeholder.metric(get_main_label("detection_time"), self.detection_time)

                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_image, (self.display_width, self.display_height))

                if self.display_mode == display_modes[0]:
                    self.image_placeholder.image(
                        resized_image,
                        channels="BGR",
                        caption=f"{get_image_display_label('detection_view')}: {self.uploaded_file.name}",
                    )
                else:
                    self.image_placeholder.image(
                        resized_frame,
                        channels="BGR",
                        caption=f"{get_image_display_label('original_view')}: {self.uploaded_file.name}",
                    )
                    if hasattr(self, "image_placeholder_res"):
                        self.image_placeholder_res.image(
                            resized_image,
                            channels="BGR",
                            caption=f"{get_image_display_label('detection_view')}: {self.uploaded_file.name}",
                        )

                # 添加到日志表（现在img_path不为None）
                self.logTable.add_frames(image, detInfo, processed_image, self.uploaded_file.name, img_path)

                status_info.write(get_general_message("updating_interface"))
                single_progress.progress(0.9)

                # 立即更新session state以确保UI同步
                st.session_state["saved_images_ini"] = self.logTable.saved_images_ini.copy()
                st.session_state["saved_images"] = self.logTable.saved_images.copy()
                st.session_state["saved_names"] = self.logTable.saved_names.copy()
                # 同步每张图片的目标信息
                if hasattr(self.logTable, "saved_targets_info"):
                    st.session_state["saved_targets_info"] = self.logTable.saved_targets_info.copy()

                # 确保索引重置为0
                st.session_state["image_play_index"] = 0

                # 更新历史日志显示
                if hasattr(self, "log_table_placeholder"):
                    self.logTable.update_table(self.log_table_placeholder)

                single_progress.progress(1.0)
                status_info.success(
                    get_detection_message(
                        "single_image_detection_complete",
                        count=len(detInfo),
                        time=self.detection_time,
                    )
                )

                st.success(get_detection_message("single_image_complete"))
                # 立即刷新页面，让selectbox自动更新
                st.rerun()

                # 立即显示检测结果
                self.toggle_comboBox(0)

                st.success(get_detection_message("image_detection_complete"))

            except Exception as e:
                st.error(get_file_message("single_image_processing_error", error=str(e)))

    def _process_video_input(self):
        """
        处理视频输入
        """
        if not hasattr(self, "uploaded_video") or not self.uploaded_video:
            st.warning(get_file_message("upload_video_first"))
            return

        self.logTable.clear_frames()
        self.progress_bar.progress(0)
        self.close_flag = self.close_placeholder.button(label=get_button_text("stop"))

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
            st.error(get_video_message("video_processing_error", error=str(e)))

    def _process_single_video(self, video_file, video_index):
        """处理单个视频文件"""
        display_modes = get_main_option("display_modes")
        try:
            # 创建临时文件
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(video_file.read())
            tfile.flush()

            cap = cv2.VideoCapture(tfile.name)
            if not cap.isOpened():
                st.error(get_video_message("video_open_failed", video_name=video_file.name))
                return

            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            current_frame = 0

            st.info(
                get_video_message(
                    "video_processing_start",
                    video_name=video_file.name,
                    total_frames=total_frames,
                )
            )

            while (
                cap.isOpened() and not self.close_flag and current_frame < total_frames
            ):
                ret, frame = cap.read()
                if not ret:
                    break

                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)

                # 进行检测
                framecopy = processed_frame.copy()
                current_time = current_frame / fps if fps > 0 else 0
                time_str = f"{int(current_time // 3600):02d}:{int((current_time % 3600) // 60):02d}:{int(current_time % 60):02d}"

                image, detInfo, _ = self.frame_process(
                    framecopy, f"{video_file.name}_{current_frame}", video_time=time_str
                )

                # 更新状态
                st.session_state["current_frame_count"] = current_frame + 1
                st.session_state["current_target_count"] = len(detInfo)
                st.session_state["current_detection_time"] = self.detection_time

                # 更新显示
                self.frame_count_placeholder.metric(get_main_label("current_frame"), current_frame + 1)
                self.target_count_placeholder.metric(get_main_label("target_count"), len(detInfo))
                self.detection_time_placeholder.metric(get_main_label("detection_time"), self.detection_time)

                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))

                if self.display_mode == display_modes[0]:
                    self.image_placeholder.image(
                        resized_image,
                        channels="BGR",
                        caption=f"{get_image_display_label('detection_view')}: {video_file.name}",
                    )
                else:
                    self.image_placeholder.image(
                        resized_frame,
                        channels="BGR",
                        caption=f"{get_image_display_label('original_view')}: {video_file.name}",
                    )
                    if hasattr(self, "image_placeholder_res"):
                        self.image_placeholder_res.image(
                            resized_image,
                            channels="BGR",
                            caption=f"{get_image_display_label('detection_view')}: {video_file.name}",
                        )

                # 添加到日志表（视频帧没有完整路径）
                self.logTable.add_frames(
                    image,
                    detInfo,
                    processed_frame,
                    f"{video_file.name}_{current_frame}",
                    None,
                )

                # 更新进度条
                progress = int((current_frame / total_frames) * 100)
                self.progress_bar.progress(progress)

                current_frame += 1

            cap.release()
            os.unlink(tfile.name)  # 删除临时文件

        except Exception as e:
            st.error(
                get_video_message(
                    "single_video_processing_error",
                    video_name=video_file.name,
                    error=str(e),
                )
            )

    def _process_camera_input(self, camera_id):
        """
        处理摄像头输入
        """
        display_modes = get_main_option("display_modes")
        try:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                st.error(get_camera_message("camera_open_failed", camera_id=camera_id))
                return

            st.info(get_camera_message("camera_started", camera_id=camera_id))
            self.close_flag = self.close_placeholder.button(
                label=get_button_text("stop")
            )

            frame_count = 0
            while cap.isOpened() and not self.close_flag:
                ret, frame = cap.read()
                if not ret:
                    st.error(get_camera_message("camera_read_frame_failed"))
                    break

                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)

                # 进行检测
                framecopy = processed_frame.copy()
                image, detInfo, _ = self.frame_process(framecopy, f"camera_{frame_count}")

                # 更新状态
                st.session_state["current_frame_count"] = frame_count + 1
                st.session_state["current_target_count"] = len(detInfo)
                st.session_state["current_detection_time"] = self.detection_time

                # 更新显示
                self.frame_count_placeholder.metric(get_main_label("current_frame"), frame_count + 1)
                self.target_count_placeholder.metric(get_main_label("target_count"), len(detInfo))
                self.detection_time_placeholder.metric(get_main_label("detection_time"), self.detection_time)

                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))

                if self.display_mode == display_modes[0]:
                    self.image_placeholder.image(
                        resized_image,
                        channels="BGR",
                        caption=get_sidebar_label("camera_detection_view"),
                    )
                else:
                    self.image_placeholder.image(
                        resized_frame,
                        channels="BGR",
                        caption=get_sidebar_label("camera_original_view"),
                    )
                    if hasattr(self, "image_placeholder_res"):
                        self.image_placeholder_res.image(
                            resized_image,
                            channels="BGR",
                            caption=get_sidebar_label("camera_detection_view"),
                        )

                # 添加到日志表（摄像头帧没有完整路径）
                self.logTable.add_frames(
                    image, detInfo, processed_frame, f"camera_{frame_count}", None
                )

                frame_count += 1
                time.sleep(0.1)  # 控制帧率

            cap.release()

        except Exception as e:
            st.error(get_camera_message("camera_processing_error", error=str(e)))

    def _process_rtsp_input(self, rtsp_url):
        """
        处理RTSP/RTMP流输入
        """
        display_modes = get_main_option("display_modes")
        try:
            cap = cv2.VideoCapture(rtsp_url)
            if not cap.isOpened():
                st.error(get_rtsp_message("rtsp_connection_failed", rtsp_url=rtsp_url))
                return

            st.info(get_rtsp_message("rtsp_connected", rtsp_url=rtsp_url))
            self.close_flag = self.close_placeholder.button(label=get_button_text("stop"))

            frame_count = 0
            while cap.isOpened() and not self.close_flag:
                ret, frame = cap.read()
                if not ret:
                    st.warning(get_rtsp_message("rtsp_stream_interrupted"))
                    time.sleep(2)
                    continue

                # 应用图像处理
                processed_frame = self.apply_image_processing(frame)

                # 进行检测
                framecopy = processed_frame.copy()
                image, detInfo, _ = self.frame_process(framecopy, f"rtsp_{frame_count}")

                # 更新状态
                st.session_state["current_frame_count"] = frame_count + 1
                st.session_state["current_target_count"] = len(detInfo)
                st.session_state["current_detection_time"] = self.detection_time

                # 更新显示
                self.frame_count_placeholder.metric(get_main_label("current_frame"), frame_count + 1)
                self.target_count_placeholder.metric(get_main_label("current_target"), len(detInfo))
                self.detection_time_placeholder.metric(get_main_label("current_detection_time"), self.detection_time)

                # 显示图片
                resized_image = cv2.resize(image, (self.display_width, self.display_height))
                resized_frame = cv2.resize(processed_frame, (self.display_width, self.display_height))

                if self.display_mode == display_modes[0]:
                    self.image_placeholder.image(
                        resized_image,
                        channels="BGR",
                        caption=get_sidebar_label("rtsp_detection_view"),
                    )
                else:
                    self.image_placeholder.image(
                        resized_frame,
                        channels="BGR",
                        caption=get_sidebar_label("rtsp_original_view"),
                    )
                    if hasattr(self, "image_placeholder_res"):
                        self.image_placeholder_res.image(
                            resized_image,
                            channels="BGR",
                            caption=get_sidebar_label("rtsp_detection_view"),
                        )

                # 添加到日志表（RTSP帧没有完整路径）
                self.logTable.add_frames(
                    image, detInfo, processed_frame, f"rtsp_{frame_count}", None
                )

                frame_count += 1
                time.sleep(0.05)  # 控制帧率

            cap.release()

        except Exception as e:
            st.error(get_rtsp_message("rtsp_processing_error", error=str(e)))
