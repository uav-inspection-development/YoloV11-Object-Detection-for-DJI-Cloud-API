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

        # 初始化类别标签列表和为每个类别随机分配颜色
        self.cls_name = Visible_type
        self.detect_class_color = Visible_class_colors
        self.colors = [self.detect_class_color.get(class_name, (0, 255, 0)) for class_name in self.cls_name.values()]
        self.selected_class_ids = None  # 选定的类别索引

        # 设置页面标题
        self.title = "光伏云组件检测系统"
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
        self.model_type = "检测任务"
        self.conf_threshold = 0.15  # 默认置信度阈值
        self.iou_threshold = 0.5  # 默认IOU阈值
        self.image_type = "可见光"  # 图像类型

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
        self.image_enhancement_method = "不处理"  # 图像增强方法

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
        self.undistortion_method = "不去除"
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
        self.model_type = self.api_params.get("model_type", "检测任务")
        self.image_type = self.api_params.get("image_type", "可见光")
        self.selected_classes = self.api_params.get("selected_classes", list(Visible_type.keys()))
        self.enable_pseudo_color = self.api_params.get("enable_pseudo_color", False)
        self.enable_rotate_correction = self.api_params.get("enable_rotate_correction", False)
        self.enable_auto_keystone_correction = self.api_params.get("enable_auto_keystone_correction", False)
        self.enable_background_fill = self.api_params.get("enable_background_fill", False)
        self.image_enhancement_method = self.api_params.get("image_enhancement_method", "不处理")
        self.undistortion_method = self.api_params.get("undistortion_method", "不去除")

        # 通过API方式上传相机标定文件
        if self.undistortion_method == "相机参数计算":
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
                    print("相机标定参数加载成功！")
                except Exception as e:
                    print(f"标定文件解析失败: {e}")
                    self.camera_matrix = None
                    self.dist_coeffs = None
                    self.calibration_file = None
            else:
                self.camera_matrix = None
                self.dist_coeffs = None
                self.calibration_file = None
        elif self.undistortion_method == "手动调整参数":
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
        if self.model_type == "分割任务":
            self.cls_name = Segmentation_type
            self.detect_class_color = Segmentation_class_colors
        else:
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
                st.warning("⚠️ 警告: 颜色列表长度与模型类别不一致！将使用随机颜色填充。")

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
        with st.sidebar.expander("📖 关于", expanded=False):
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
        st.sidebar.title("🔧 设置菜单")

        # Add the About section to the sidebar
        self.show_about_section()

        # 添加登录设置
        st.sidebar.header("🔒 登陆设置")
        if st.sidebar.button("🚪 退出登陆"):
            st.session_state.clear()
            if os.path.exists("login_cache.json"):
                os.remove("login_cache.json")
            st.rerun()

        # 添加显示设置
        st.sidebar.header("🖥️ 显示设置")

        # 添加固定比例选项
        aspect_ratio = st.sidebar.selectbox("选择显示比例", options=["16:9", "4:3", "自由调整"], index=0)
        if aspect_ratio == "16:9":
            ratio = 16 / 9
        elif aspect_ratio == "4:3":
            ratio = 4 / 3
        else:
            ratio = None  # 自由调整

        # 根据选择的比例调整宽度和高度
        if ratio:
            # 用户输入高度时自动调整宽度
            self.new_height = st.sidebar.number_input("输入显示高度 (默认: 1080)", min_value=100, max_value=2160, value=1080, step=10)
            self.new_width = int(self.new_height * ratio)
            st.sidebar.number_input("输入显示宽度", value=self.new_width, disabled=True)
        else:
            # 自由调整模式
            self.new_width = st.sidebar.number_input("输入显示宽度 (默认: 1080)", min_value=100, max_value=3840, value=1080, step=10)
            self.new_height = st.sidebar.number_input("输入显示高度 (默认: 720)", min_value=100, max_value=2160, value=720, step=10)

        # 添加 CSV 输出路径设置
        st.sidebar.header("📂 日志保存路径设置")
        self.csv_output_path = st.sidebar.text_input(
            "输出日志保存路径",
            value=abs_path("../output/logs", path_type="current"),  # 默认路径
            placeholder="例如：D:/output/logs"
        )

        # 确保路径以斜杠结尾
        if not self.csv_output_path.endswith(os.sep):
            self.csv_output_path += os.sep

        st.sidebar.header("📤 日志导出格式设置")
        self.export_format = st.sidebar.radio("选择导出格式", options=["Word", "CSV", "Excel", "JSON"], index=0)
        st.sidebar.caption(f"💡 提示: {self.export_format} 文件将导出至 {self.csv_output_path} 路径。")

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
            st.write("未找到可用的摄像头")

        # 初始化或获取识别结果的表格
        self.logTable = st.session_state['logTable']
        self.model = st.session_state['model']

        st.sidebar.header("⚙️ 检测阈值设定")
        # 置信度阈值的滑动条
        self.conf_threshold = float(st.sidebar.slider("置信度设定", min_value=0.0, max_value=1.0, value=0.15))
        st.sidebar.caption("💡 提示: 置信度设定范围为0.0到1.0，代表检测结果的置信度。")
        # IOU阈值的滑动条
        self.iou_threshold = float(st.sidebar.slider("IOU设定", min_value=0.0, max_value=1.0, value=0.25))
        st.sidebar.caption("💡 提示: IOU设定范围为0.0到1.0，代表检测结果的重叠度。")
        # 设置侧边栏的模型设置部分
        st.sidebar.header("🧠 模型设置")
        # 选择模型类型的下拉菜单
        self.model_type = st.sidebar.radio("选择任务类型", options=["检测任务", "分割任务"], index=0)

        available_options = []
        # 添加提示信息
        if self.model_type == "检测任务":
            st.sidebar.caption("💡 提示: 检测任务将检测异常的光伏板组件或其他异常，目标类别按实际需要选择。")
            available_options = ["EL隐裂", "红外", "可见光", "其他"]
        elif self.model_type == "分割任务":
            self.rectangle_bounding_output = st.sidebar.checkbox("输出矩形边框", value=True)
            st.sidebar.caption("💡 提示: 分割任务将对所有的光伏板轮廓进行分割，选择输出矩形边框后，将检测矩形边框并输出，否则输出原始边缘，目标类别选择【单组件】或【组串】即可。")
            available_options = ["红外", "可见光"]

        # 添加图像类型选择
        st.sidebar.header("🖼️ 图像类型选择")
        self.image_type = st.sidebar.radio(
            "选择图像类型",
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
        st.sidebar.caption(f"💡 提示: 当前选择的图像类型为: {self.image_type}")

        # 设置侧边栏的选择需要检测的目标类别部分，默认选择所有类别
        st.sidebar.header("🎯 目标类别选择")
        self.available_classes = list(self.cls_name.values())
        self.available_class_keys = list(self.cls_name.keys())
        self.selected_classes = st.sidebar.multiselect(
            "选择需要检测或分割的目标类别",
            options=self.available_classes,
            default=self.available_classes  # 默认选择所有类别
        )

        # 将选定的类别转换为索引
        self.selected_class_ids = [
            idx for idx, name in enumerate(self.model.names) if name in self.selected_classes
        ]

        # 添加提示信息
        if len(self.selected_classes) == 0:
            st.sidebar.caption("💡 提示: 未选择任何类别，模型将不会检测任何目标。")
        else:
            st.sidebar.caption(f"💡 提示: 当前选择的类别为: {', '.join(self.selected_classes)}")

        # 映射中文名称到英文名称
        self.selected_classes = [
            english_name for english_name, chinese_name in self.cls_name.items() if chinese_name in self.selected_classes
        ]

        # 选择模型文件类型，可以是默认的或者自定义的
        st.sidebar.header("📁 模型文件设置")
        model_file_option = st.sidebar.radio("模型设置", options=["默认", "指定权重文件"], index=0)
        if model_file_option == "指定权重文件":
            # 如果选择自定义模型文件，则提供文件上传器
            model_file = st.sidebar.file_uploader("选择.pt文件", type="pt")

            # 如果上传了模型文件，则保存并加载该模型
            if model_file is not None:
                self.custom_model_file = save_uploaded_file(model_file)
                try:
                    self.model.load_model(model_path=self.custom_model_file)
                except Exception as e:
                    st.sidebar.error(f"⚠️ 错误: 无法加载模型文件，请检查文件格式或路径是否正确！错误信息: {str(e)}")
                # 检查模型类别是否与选定类别一致
                if set(self.model.names) != set(self.available_class_keys):
                    st.sidebar.error("⚠️ 错误: 模型类别与选定类别不匹配，请检查模型文件或重新选择类别！")
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
                    st.sidebar.error("⚠️ 错误: 不支持的图像类型！")

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
                    st.warning("⚠️ 警告: 颜色列表长度与模型类别不一致！将使用随机颜色填充。")

            except Exception as e:
                st.sidebar.error(f"⚠️ 错误: 无法加载默认模型文件，请检查文件路径或文件是否存在！错误信息: {str(e)}")

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
                st.sidebar.warning(f"⚠️ 警告: 模型类别与选定类别已自动调整！")
            else:
                # 为模型中的类别重新分配颜色
                self.colors = [
                    self.detect_class_color.get(class_name, [random.randint(0, 255) for _ in range(3)])
                    for class_name in self.model.names
                ]

        # 设置侧边栏的摄像头和 RTSP/RTMP 配置部分
        st.sidebar.header("📹 输入源识别设置")
        # 选择输入源类型：无输入，摄像头或 RTSP/RTMP 流
        self.input_source = st.sidebar.radio("选择输入源", options=["图片文件", "图片文件夹", "视频文件", "视频文件夹", "摄像头", "RTSP/RTMP流"], index=0)

        if "file_key" not in st.session_state:
            st.session_state["file_key"] = str(random.random())

        if self.input_source == "摄像头":
            # 选择摄像头的下拉菜单
            self.selected_camera = st.sidebar.selectbox("选择摄像头序号", self.available_cameras)
            st.sidebar.caption("💡 提示: 请点击'开始检测'按钮，启动摄像头检测！")
        elif self.input_source == "RTSP/RTMP流":
            # 输入 RTSP/RTMP 地址
            self.rtsp_input_url = st.sidebar.text_input("输入RTSP/RTMP地址", placeholder="例如：rtsp://<ip>:<port>/path 或 rtmp://<ip>:<port>/path")
            st.sidebar.caption("💡 提示: 请点击'开始检测'按钮，启动RTSP/RTMP流检测！")
        elif self.input_source == "图片文件":
            self.uploaded_file = st.sidebar.file_uploader("上传图片", type=["jpg", "png", "jpeg"], accept_multiple_files=True, key=st.session_state["file_key"])
            st.sidebar.write(f"📂 已上传图片数量: {len(self.uploaded_file)}")
            st.sidebar.caption("💡 提示: 请选择图片并点击'开始运行'按钮，进行图片检测！")
        elif self.input_source == "图片文件夹":
            default_types = ["jpg", "jpeg", "png"]
            image_types = st.sidebar.multiselect(
                "选择图片类型", 
                options=["jpg", "jpeg", "png", "bmp", "tif", "tiff", "webp"], 
                default=default_types
            )

            # Tkinter文件夹选择器按钮
            if st.sidebar.button("📂 选择图片文件夹"):
                root = tk.Tk()
                root.withdraw()
                root.wm_attributes('-topmost', 1)
                folder_path = filedialog.askdirectory(master=root)
                root.destroy()
                if folder_path:
                    st.session_state['image_folder_path'] = folder_path

            folder_path = st.sidebar.text_input(
                "输入图片文件夹路径", 
                value=st.session_state.get('image_folder_path', ''), 
                placeholder="例如：D:/images"
            )
            image_files = []
            if folder_path and os.path.isdir(folder_path):
                exts = tuple(f".{ext.lower()}" for ext in image_types)
                for root_dir, _, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(exts):
                            image_files.append(os.path.join(root_dir, file))
                st.sidebar.write(f"📂 共找到图片数量: {len(image_files)}")
                # 转为文件对象
                self.uploaded_file = [LocalFileObj(f) for f in image_files]
            else:
                st.sidebar.caption("💡 提示: 选择或输入本地图片文件夹路径，自动递归查找所有图片。")
                self.uploaded_file = []
        elif self.input_source == "视频文件":
            self.uploaded_video = st.sidebar.file_uploader("上传视频文件", type=["mp4", "avi", "mov"], accept_multiple_files=True, key=st.session_state["file_key"])
            st.sidebar.write(f"📂 已上传视频数量: {len(self.uploaded_video)}")
            st.sidebar.caption("💡 请选择视频并点击'开始运行'按钮，进行视频检测！")
        elif self.input_source == "视频文件夹":
            default_video_types = ["mp4", "avi", "mov"]
            video_types = st.sidebar.multiselect(
                "选择视频类型",
                options=["mp4", "avi", "mov", "mkv", "flv", "wmv"],
                default=default_video_types
            )
            # Tkinter文件夹选择器按钮
            if st.sidebar.button("选择视频文件夹"):
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
                for uploaded_file in self.uploaded_file:
                    source_img = uploaded_file.read()
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

                    # Display original and distorted images for each file
                    st.sidebar.image([image_ini, distorted_image], caption=[f"原始图像: {uploaded_file.name}", f"调整后的图像: {uploaded_file.name}"], channels="BGR")
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
            st.sidebar.warning("💡 请先上传图像以调整畸变系数。")

        st.sidebar.header("📁 输出文件路径设置")
        self.output_path = st.sidebar.text_input("输出文件路径", value=abs_path("../output", path_type="current"), placeholder="例如：../output 或 D:/videos")

        if self.input_source in ["摄像头", "RTSP/RTMP流"]:
            st.sidebar.header("📡 RTSP/RTMP输出设置")
            self.enable_rtsp_output = st.sidebar.checkbox("启用RTSP/RTMP输出", value=False)

            # RTSP/RTMP输出地址输入
            if self.enable_rtsp_output:
                self.rtsp_output_url = st.sidebar.text_input("RTSP/RTMP输出地址", placeholder="例如：rtmp://<ip>:<port>/live/stream 或 rtsp://<ip>:<port>/path")
                st.sidebar.write("💡 提示: 设置RTSP/RTMP输出地址，将流视频检测结果推送至RTSP/RTMP客户端，例如：rtmp://<ip>:<port>/live/stream")

    def process_camera_or_file(self):
        """
        根据用户选择的输入源（摄像头、图片文件、视频文件或RTSP/RTMP流），处理并显示检测结果。
        """
        if self.input_source in ["摄像头", "RTSP/RTMP流"]:
            self._process_stream()
        elif self.input_source == "图片文件" or self.input_source == "图片文件夹":
            # 确保上传文件为列表
            files = self.uploaded_file if isinstance(self.uploaded_file, list) else [self.uploaded_file]
            for f in files:
                if f: f.seek(0)
            self._process_image_input()
        elif self.input_source == "视频文件" or self.input_source == "视频文件夹":
            files = self.uploaded_video if isinstance(self.uploaded_video, list) else [self.uploaded_video]
            for f in files:
                if f: f.seek(0)
            self._process_video_input()
        else:
            st.warning("请选择有效的输入源！")

    def _process_stream(self):
        """
        处理摄像头或 RTSP/RTMP 流。
        """
        if self.input_source == "摄像头":
            input_type = "camera"
            # 使用 OpenCV 捕获摄像头画面
            if str(self.selected_camera) == '0':
                input_source = 0
            else:
                if len(self.selected_camera) < 8:
                    try:
                        input_source = int(self.selected_camera)
                    except:
                        st.warning("请检查摄像头序号")
                else:
                    input_source = self.selected_camera
        elif self.input_source == "RTSP/RTMP流":
            input_type = "stream"
            if not self.rtsp_input_url:
                st.warning("请输入有效的RTSP/RTMP地址！")
                return
            input_source = self.rtsp_input_url
        self.logTable.clear_frames()  # 清除之前的帧记录
        # 创建一个结束按钮
        self.close_flag = self.close_placeholder.button(label="停止")

        cap = cv2.VideoCapture(input_source)

        if not cap.isOpened():
            st.error(f"无法打开{self.input_source}，请检查地址或设备连接！")
            return

        self.uploaded_video = None

        fps = cap.get(cv2.CAP_PROP_FPS)

        self.FPS = fps

        # 设置总帧数为1000
        total_frames = 1000
        current_frame = 0
        self.progress_bar.progress(0)  # 初始化进度条

        try:

            cap = cv2.VideoCapture(input_source)

            if not cap.isOpened():
                st.error(f"无法打开摄像头或RTSP/RTMP流，请检查地址或设备连接！")
                return

            # 获取视频属性
            fps = cap.get(cv2.CAP_PROP_FPS)
            self.FPS = fps

            # 创建进度条
            self.progress_bar.progress(0)

            # 创建保存文件的信息
            if not os.path.exists(self.output_path):
                os.makedirs(self.output_path)

            if self.enable_video_output:
                ret, frame = cap.read()
                height, width, layers = frame.shape
                size = (width, height)
                
                # 设置视频保存路径，使用当前时间作为文件名后缀
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                file_name = os.path.join(self.output_path, "/video/", f"{input_type}_{current_time}.avi")
                d_file_name = os.path.dirname(file_name)
                if not os.path.exists(d_file_name):
                    os.makedirs(d_file_name)
                video_out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'DIVX'), fps, size)

                if not video_out.isOpened():
                    st.error("无法打开视频输出流，请检查路径或文件权限！")
                    return

            if self.enable_rtsp_output:
                # 设置RTSP/RTMP输出流
                stream_out = cv2.VideoWriter(self.rtsp_output_url, cv2.VideoWriter_fourcc(*'H264'), fps, size)

                if not stream_out.isOpened():
                    st.error("无法打开RTSP/RTMP输出流，请检查服务器配置！")
                    return

            while cap.isOpened() and not self.close_flag:
                ret, frame = cap.read()
                if ret:
                    # 去畸变
                    if self.undistortion_method == "相机参数计算":
                        frame = camera_undistortion(frame, self.camera_matrix, self.dist_coeffs)
                    elif self.undistortion_method == "手动调整参数":
                        frame = auto_undistort_image(frame, self.image_k1)

                    # 梯形校正
                    if self.enable_rotate_correction:
                        frame = rotate_image(frame, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)

                    if self.enable_auto_keystone_correction:
                        frame = auto_keystone_correction(frame, scale_factor=self.scale_factor_keystone)

                    if self.enable_background_fill:
                        frame = fill_largest_polygon_white(frame, scale_factor=self.scale_factor_fill)

                    # 图像增强
                    if self.image_enhancement_method == "CLAHE":
                        frame = enhance_texture(frame, method="clahe")
                    elif self.image_enhancement_method == "Histogram Equalization":
                        frame = enhance_texture(frame, method="histogram_equalization")

                    # 调节摄像头的分辨率
                    # 调整图像尺寸
                    frame = cv2.resize(frame, (self.new_width, self.new_height))

                    # 检查图像是否为黑白图像
                    is_bw = is_black_and_white(frame)
                    # 如果启用了伪彩色转换，应用转换
                    if self.enable_pseudo_color and is_bw:
                        frame = convert_to_pseudo_colorizer(frame, contrast=self.image_contrast, brightness=self.image_brightness)

                    framecopy = frame.copy()
                    image, detInfo, _ = self.frame_process(framecopy, input_type)

                    # 更新检测结果并存储到 st.session_state
                    st.session_state['current_frame_count'] = current_frame
                    st.session_state['current_fps'] = self.FPS
                    st.session_state['current_target_count'] = len(detInfo)
                    st.session_state['current_detection_time'] = self.detection_time

                    # 更新检测结果
                    self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
                    self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
                    self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
                    self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

                    # 保存目标结果图片
                    if detInfo:
                        file_name = abs_path(self.output_path + '/image/' + str(current_frame + 1) + '.jpg', path_type="current")
                        save_chinese_image(file_name, image)

                    if self.enable_video_output:
                        # 保存目标结果视频
                        video_out.write(image)

                    if self.enable_rtsp_output:
                        # 保存RTSP/RTMP输出流
                        stream_out.write(image)

                    # 调整图像尺寸
                    resized_image = cv2.resize(image, (self.new_width, self.new_height))
                    resized_frame = cv2.resize(frame, (self.new_width, self.new_height))
                    if self.display_mode == "叠加显示":
                        self.image_placeholder.image(resized_image, channels="BGR", caption="识别画面")
                    else:
                        self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面")
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面")

                    self.logTable.add_frames(image, detInfo, frame, input_type + f"_{current_frame}")

                    # 更新进度条
                    progress_percentage = int((current_frame / total_frames) * 100)
                    self.progress_bar.progress(progress_percentage)
                    current_frame = (current_frame + 1) % total_frames  # 重置进度条
                else:
                    break

            self.logTable.update_table(self.log_table_placeholder)
        finally:
            cap.release()
            if self.enable_video_output:
                video_out.release()
            if self.enable_rtsp_output:
                stream_out.release()
            if self.uploaded_video is None:
                name_in = None
            else:
                name_in = self.uploaded_video.name

            res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in, output_path=self.output_path + '/frame/')
            if res:
                st.write(f"结果的目标文件已经保存：{res}")

    def _process_image_input(self):
        """
        处理上传的图片文件。
        """
        # 如果上传了图片文件
        if self.uploaded_file:
            # output/image/xxx.jpg

            self.logTable.clear_frames()
            self.progress_bar.progress(0)

            # 检查是否上传了多个文件
            if isinstance(self.uploaded_file, list):
                # 批量处理上传的图片
                for idx, uploaded_file in enumerate(self.uploaded_file):
                    # 处理每个上传的图片文件
                    source_img = uploaded_file.read()
                    if not source_img:
                        st.error(f"文件 {uploaded_file.name} 读取失败或为空！")
                        continue
                    file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                    image_ini = cv2.imdecode(file_bytes, 1)
                    # 去畸变
                    if self.undistortion_method == "相机参数计算":
                        image_ini = camera_undistortion(image_ini, self.camera_matrix, self.dist_coeffs)
                    elif self.undistortion_method == "手动调整参数":
                        image_ini = auto_undistort_image(image_ini, self.image_k1)

                    # 梯形校正
                    if self.enable_rotate_correction:
                        image_ini = rotate_image(image_ini, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)

                    if self.enable_auto_keystone_correction:
                        image_ini = auto_keystone_correction(image_ini, scale_factor=self.scale_factor_keystone)

                    if self.enable_background_fill:
                        image_ini = fill_largest_polygon_white(image_ini, scale_factor=self.scale_factor_fill)

                    # 图像增强
                    if self.image_enhancement_method == "CLAHE":
                        image_ini = enhance_texture(image_ini, method="clahe")
                    elif self.image_enhancement_method == "Histogram Equalization":
                        image_ini = enhance_texture(image_ini, method="histogram_equalization")

                    # 检查图像是否为黑白图像
                    is_bw = is_black_and_white(image_ini)
                    # 如果启用了伪彩色转换，应用转换
                    if self.enable_pseudo_color and is_bw:
                        image_ini = convert_to_pseudo_colorizer(image_ini, contrast=self.image_contrast, brightness=self.image_brightness)

                    framecopy = image_ini.copy()
                    image, detInfo, select_info = self.frame_process(framecopy, uploaded_file.name)
                    save_chinese_image(self.output_path + '/image/' + uploaded_file.name, image)

                    # 更新检测结果并存储到 st.session_state
                    st.session_state['current_frame_count'] = idx + 1
                    st.session_state['current_fps'] = 0
                    st.session_state['current_target_count'] = len(detInfo)
                    st.session_state['current_detection_time'] = self.detection_time

                    # 更新检测结果
                    self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
                    self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
                    self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
                    self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

                    # 调整图像尺寸
                    resized_image = cv2.resize(image, (self.new_width, self.new_height))
                    resized_frame = cv2.resize(image_ini, (self.new_width, self.new_height))
                    if self.display_mode == "叠加显示":
                        self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {uploaded_file.name}")
                    else:
                        self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {uploaded_file.name}")
                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {uploaded_file.name}")

                    self.logTable.add_frames(image, detInfo, image_ini, uploaded_file.name)
                    # 更新进度条
                    progress_percentage = int(((idx + 1) / len(self.uploaded_file)) * 100)
                    self.progress_bar.progress(progress_percentage)

                st.session_state['saved_images_ini'] = self.logTable.saved_images_ini
                st.session_state['saved_images'] = self.logTable.saved_images
                st.session_state['saved_names'] = self.logTable.saved_names
                st.success("批量图片检测完成！")

            else:
                # 单个文件处理
                source_img = self.uploaded_file.read()
                if not source_img:
                    st.error(f"文件 {self.uploaded_file.name} 读取失败或为空！")
                    return
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)
                # 去畸变
                if self.undistortion_method == "相机参数计算":
                    image_ini = camera_undistortion(image_ini, self.camera_matrix, self.dist_coeffs)
                elif self.undistortion_method == "手动调整参数":
                    image_ini = auto_undistort_image(image_ini, self.image_k1)

                # 梯形校正
                if self.enable_rotate_correction:
                    image_ini = rotate_image(image_ini, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)

                if self.enable_auto_keystone_correction:
                    image_ini = auto_keystone_correction(image_ini, scale_factor=self.scale_factor_keystone)

                if self.enable_background_fill:
                    image_ini = fill_largest_polygon_white(image_ini, scale_factor=self.scale_factor_fill)

                # 图像增强
                if self.image_enhancement_method == "CLAHE":
                    image_ini = enhance_texture(image_ini, method="clahe")
                elif self.image_enhancement_method == "Histogram Equalization":
                    image_ini = enhance_texture(image_ini, method="histogram_equalization")

                # 检查图像是否为黑白图像
                is_bw = is_black_and_white(image_ini)
                # 如果启用了伪彩色转换，应用转换
                if self.enable_pseudo_color and is_bw:
                    image_ini = convert_to_pseudo_colorizer(image_ini, contrast=self.image_contrast, brightness=self.image_brightness)

                framecopy = image_ini.copy()
                image, detInfo, select_info = self.frame_process(framecopy, self.uploaded_file.name)
                save_chinese_image(self.output_path + '/image/' + self.uploaded_file.name, image)

                # 更新检测结果并存储到 st.session_state
                st.session_state['current_frame_count'] = 0
                st.session_state['current_fps'] = 0
                st.session_state['current_target_count'] = len(detInfo)
                st.session_state['current_detection_time'] = self.detection_time

                # 更新检测结果
                self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
                self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
                self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
                self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

                # 调整图像尺寸
                resized_image = cv2.resize(image, (self.new_width, self.new_height))
                resized_frame = cv2.resize(image_ini, (self.new_width, self.new_height))
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_file.name}")
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {self.uploaded_file.name}")
                    self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_file.name}")

                self.logTable.add_frames(image, detInfo, image_ini, self.uploaded_file.name)
                self.progress_bar.progress(100)

                st.session_state['saved_images_ini'] = self.logTable.saved_images_ini
                st.session_state['saved_images'] = self.logTable.saved_images
                st.session_state['saved_names'] = self.logTable.saved_names
                st.success("单张图片检测完成！")

            self.selectbox_target = self.selectbox_placeholder.selectbox("目标过滤", select_info)

            self.logTable.update_table(self.log_table_placeholder)  # 更新所有结果记录的表格
        else:
            st.warning("请上传图片文件！")

    def _process_video_input(self):
        """
        处理上传的视频文件。
        """
        if self.uploaded_video:
            # output/video_name/video/xxx.avi

            # 处理上传的视频
            self.logTable.clear_frames()
            self.progress_bar.progress(0)

            self.close_flag = self.close_placeholder.button(label="停止")

            # 检查是否上传了多个视频文件
            if isinstance(self.uploaded_video, list):
                for idx, uploaded_video in enumerate(self.uploaded_video):
                    # 处理每个上传的视频文件
                    video_file = uploaded_video
                    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                    try:
                        tfile.write(video_file.read())
                        tfile.flush()

                        tfile.seek(0)  # 确保文件指针回到文件开头

                        cap = cv2.VideoCapture(tfile.name)
                        if not cap.isOpened():
                            st.error(f"无法打开视频文件: {uploaded_video.name}")
                            continue  # Skip to the next file

                        # 获取视频总帧数和帧率
                        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        self.FPS = fps
                        total_length = total_frames / fps if fps > 0 else 0
                        print(f'视频时长：{total_length:.2f}s')
                        self.progress_bar.progress(0)

                        current_frame = 0

                        # 创建保存文件的信息
                        video_savepath = self.output_path + '/' + uploaded_video.name
                        if not os.path.exists(video_savepath):
                            os.makedirs(video_savepath)

                        if self.enable_video_output:
                            ret, frame = cap.read()
                            height, width, layers = frame.shape
                            size = (width, height)
                            file_name = abs_path(video_savepath + '/video/' + uploaded_video.name + '.avi', path_type="current")
                            video_out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'DIVX'), fps, size)

                        while cap.isOpened() and not self.close_flag:
                            ret, frame = cap.read()
                            if ret:
                                # 去畸变
                                if self.undistortion_method == "相机参数计算":
                                    frame = camera_undistortion(frame, self.camera_matrix, self.dist_coeffs)
                                elif self.undistortion_method == "手动调整参数":
                                    frame = auto_undistort_image(frame, self.image_k1)
                                # 梯形校正
                                if self.enable_rotate_correction:
                                    frame = rotate_image(frame, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)

                                if self.enable_auto_keystone_correction:
                                    frame = auto_keystone_correction(frame, scale_factor=self.scale_factor_keystone)

                                if self.enable_background_fill:
                                    frame = fill_largest_polygon_white(frame, scale_factor=self.scale_factor_fill)

                                # 图像增强
                                if self.image_enhancement_method == "CLAHE":
                                    frame = enhance_texture(frame, method="clahe")
                                elif self.image_enhancement_method == "Histogram Equalization":
                                    frame = enhance_texture(frame, method="histogram_equalization")

                                # 检查是否为黑白图像
                                is_bw = is_black_and_white(frame)
                                # 如果启用了伪彩色转换，应用转换
                                if self.enable_pseudo_color and is_bw:
                                    frame = convert_to_pseudo_colorizer(frame, contrast=self.image_contrast, brightness=self.image_brightness)

                                framecopy = frame.copy()
                                current_time = current_frame / fps
                                if current_time < total_length:
                                    current_frame += 1
                                    current_time_str = format_time(current_time)
                                    image, detInfo, _ = self.frame_process(framecopy, uploaded_video.name, video_time=current_time_str)

                                    # 更新检测结果并存储到 st.session_state
                                    st.session_state['current_frame_count'] = current_frame
                                    st.session_state['current_fps'] = self.FPS
                                    st.session_state['current_target_count'] = len(detInfo)
                                    st.session_state['current_detection_time'] = self.detection_time

                                    # 更新检测结果
                                    self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
                                    self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
                                    self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
                                    self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

                                    if detInfo:
                                        time_obj = datetime.strptime(current_time_str, "%H:%M:%S")
                                        formatted_time = time_obj.strftime("%H_%M_%S")
                                        file_name = abs_path(video_savepath + '/image/' + formatted_time + '_' + str(current_frame) + '.jpg', path_type="current")
                                        save_chinese_image(file_name, image)

                                    if self.enable_video_output:
                                        video_out.write(image)

                                    # 调整图像尺寸
                                    resized_image = cv2.resize(image, (self.new_width, self.new_height))
                                    resized_frame = cv2.resize(frame, (self.new_width, self.new_height))
                                    if self.display_mode == "叠加显示":
                                        self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {uploaded_video.name}")
                                    else:
                                        self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {uploaded_video.name}")
                                        self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {uploaded_video.name}")

                                    self.logTable.add_frames(image, detInfo, frame, uploaded_video.name + f"_{current_frame}")

                                    # 更新进度条
                                    progress_percentage = int(((current_frame + 1) / total_frames) * 100)
                                    self.progress_bar.progress(progress_percentage)

                                    current_frame += 1
                            else:
                                break

                        self.logTable.update_table(self.log_table_placeholder)
                    finally:
                        cap.release()
                        if self.enable_video_output:
                            video_out.release()

                        if self.uploaded_video is None:
                            name_in = None
                        else:
                            name_in = uploaded_video.name

                        res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in, output_path=self.output_path + '/frame/')
                        if res:
                            st.write(f"结果的目标文件已经保存：{res}")

                        tfile.close()
                        # 如果不需要再保留临时文件，可以在处理完后删除
                        print(f'{tfile.name} 临时文件可以删除')
                        # os.remove(tfile.name)

                    # 更新进度条
                    batch_progress = int(((idx + 1) / len(self.uploaded_video)) * 100)
                    self.progress_bar.progress(batch_progress)

                st.session_state['saved_images_ini'] = self.logTable.saved_images_ini
                st.session_state['saved_images'] = self.logTable.saved_images
                st.session_state['saved_names'] = self.logTable.saved_names
                st.success("批量视频检测完成！")
            else:
                video_file = self.uploaded_video
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                try:
                    tfile.write(video_file.read())
                    tfile.flush()

                    tfile.seek(0)  # 确保文件指针回到文件开头

                    cap = cv2.VideoCapture(tfile.name)

                    if not cap.isOpened():
                        st.error(f"无法打开视频文件: {uploaded_video.name}")
                        return

                    # 获取视频总帧数和帧率
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    self.FPS = fps
                    # 计算视频总长度（秒）
                    total_length = total_frames / fps if fps > 0 else 0
                    print('视频时长：' + str(total_length)[:4] + 's')
                    # 创建进度条
                    self.progress_bar.progress(0)

                    current_frame = 0

                    # 创建保存文件的信息
                    video_savepath = self.output_path + '/' + self.uploaded_video.name
                    if not os.path.exists(video_savepath):
                        os.makedirs(video_savepath)

                    if self.enable_video_output:
                        ret, frame = cap.read()
                        height, width, layers = frame.shape
                        size = (width, height)
                        file_name = abs_path(video_savepath + '/video/' + self.uploaded_video.name + '.avi', path_type="current")
                        video_out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'DIVX'), fps, size)

                    while cap.isOpened() and not self.close_flag:
                        ret, frame = cap.read()
                        if ret:
                            # 去畸变
                            if self.undistortion_method == "相机参数计算":
                                frame = camera_undistortion(frame, self.camera_matrix, self.dist_coeffs)
                            elif self.undistortion_method == "手动调整参数":
                                frame = auto_undistort_image(frame, self.image_k1)

                            # 梯形校正
                            if self.enable_rotate_correction:
                                frame = rotate_image(frame, angle_x=self.rot_angle_x, angle_y=self.rot_angle_y, zoom_factor=self.keystone_scale)

                            if self.enable_auto_keystone_correction:
                                frame = auto_keystone_correction(frame, scale_factor=self.scale_factor_keystone)

                            if self.enable_background_fill:
                                frame = fill_largest_polygon_white(frame, scale_factor=self.scale_factor_fill)

                            if self.image_enhancement_method == "CLAHE":
                                frame = enhance_texture(frame, method="clahe")
                            elif self.image_enhancement_method == "Histogram Equalization":
                                frame = enhance_texture(frame, method="histogram_equalization")

                            # 检查是否为黑白图像
                            is_bw = is_black_and_white(frame)
                            # 如果启用了伪彩色转换，应用转换
                            if self.enable_pseudo_color and is_bw:
                                frame = convert_to_pseudo_colorizer(frame, contrast=self.image_contrast, brightness=self.image_brightness)

                            framecopy = frame.copy()
                            # 计算当前帧对应的时间（秒）
                            current_time = current_frame / fps
                            if current_time < total_length:
                                current_frame += 1
                                current_time_str = format_time(current_time)
                                image, detInfo, _ = self.frame_process(framecopy, self.uploaded_video.name, video_time=current_time_str)

                                # 更新检测结果并存储到 st.session_state
                                st.session_state['current_frame_count'] = current_frame
                                st.session_state['current_fps'] = self.FPS
                                st.session_state['current_target_count'] = len(detInfo)
                                st.session_state['current_detection_time'] = self.detection_time

                                # 更新检测结果
                                self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
                                self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
                                self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
                                self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

                                # 保存目标结果图片
                                if detInfo:
                                    # 将字符串转换为 datetime 对象
                                    time_obj = datetime.strptime(current_time_str, "%H:%M:%S")

                                    # 将 datetime 对象格式化为所需的字符串格式
                                    formatted_time = time_obj.strftime("%H_%M_%S")
                                    file_name = abs_path(video_savepath + '/image/' + formatted_time  + '_' + str(current_frame) + '.jpg',
                                                        path_type="current")
                                    save_chinese_image(file_name, image)

                                if self.enable_video_output:
                                    # 保存目标结果视频
                                    video_out.write(image)

                                # 调整图像尺寸
                                resized_image = cv2.resize(image, (self.new_width, self.new_height))
                                resized_frame = cv2.resize(frame, (self.new_width, self.new_height))
                                if self.display_mode == "叠加显示":
                                    self.image_placeholder.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_video.name}")
                                else:
                                    self.image_placeholder.image(resized_frame, channels="BGR", caption=f"原始画面: {self.uploaded_video.name}")
                                    self.image_placeholder_res.image(resized_image, channels="BGR", caption=f"识别画面: {self.uploaded_video.name}")

                                self.logTable.add_frames(image, detInfo, frame, self.uploaded_video.name + f"_{current_frame}")

                                # 更新进度条
                                if total_length > 0:
                                    progress_percentage = int(((current_frame + 1) / total_frames) * 100)
                                    self.progress_bar.progress(progress_percentage)

                                current_frame += 1
                        else:
                            break

                    self.logTable.update_table(self.log_table_placeholder)
                finally:
                    cap.release()
                    if self.enable_video_output:
                        video_out.release()

                    if self.uploaded_video is None:
                        name_in = None
                    else:
                        name_in = self.uploaded_video.name

                    res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in, output_path=self.output_path + '/frame/')
                    if res:
                        st.write(f"结果的目标文件已经保存：{res}")

                    tfile.close()
                    # 如果不需要再保留临时文件，可以在处理完后删除
                    print(tfile.name + ' 临时文件可以删除')
                    # os.remove(tfile.name)

                st.session_state['saved_images_ini'] = self.logTable.saved_images_ini
                st.session_state['saved_images'] = self.logTable.saved_images
                st.session_state['saved_names'] = self.logTable.saved_names
                st.success("单个视频检测完成！")
        else:
            st.warning("请上传视频文件！")

    def toggle_comboBox(self, frame_id):
        """
        处理并显示指定帧的检测结果。

        Args:
            frame_id (int): 指定要显示检测结果的帧ID。

        根据用户选择的目标过滤选项，显示该帧的检测结果和图像。
        """
        if frame_id == -1:  # 显示所有目标
            if not self.logTable.saved_images_ini:
                st.warning("没有检测结果可显示！")
                self.image_placeholder.image(load_default_image(), caption="原始画面")
                self.table_placeholder.table(pd.DataFrame(columns=["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)"]))
                return
            frame_id = 0  # 默认显示第一帧

        if len(self.logTable.saved_results) > frame_id:
            frame = self.logTable.saved_images_ini[frame_id]  # 获取指定帧的初始图像
            image = frame.copy()  # 创建图像副本以避免修改原始图像

            detection_results = self.logTable.saved_results[frame_id]  # 获取指定帧的所有检测结果
            disp_res = ResultLogger()  # 创建结果记录器

            # 获取当前选中的目标过滤选项
            selected_target = st.session_state.get('selectbox_target', "全部目标")

            if detection_results:
                cnt = 0  # 用于绘制检测框的计数器
                for detInfo in detection_results:  # 遍历当前帧的所有检测结果
                    if isinstance(detInfo, list) and len(detInfo) == 6:  # 验证结构
                        name, chinese_name, bbox, conf, use_time, cls_id = detInfo

                        # Ensure cls_id is within bounds
                        if cls_id >= len(self.colors):
                            st.warning(f"⚠️ 警告: 检测到的类别索引 {cls_id} 超出颜色列表范围！使用默认颜色。")
                            color = (255, 0, 0)  # 默认红色
                        else:
                            color = self.colors[cls_id]

                        # 如果选择了目标过滤，跳过不匹配的目标
                        if selected_target != "全部目标" and selected_target != chinese_name:
                            continue

                        # label = '%s %.0f%%' % (name, conf * 100)  # 构造标签文本

                        # 合并结果到表格
                        disp_res.concat_results(name, chinese_name, bbox, str(round(conf, 2)), str(use_time))

                        # 绘制检测框
                        info = {
                            'class_name': name,
                            'bbox': bbox,
                            'score': conf,
                            'class_id': cls_id,
                            'mask': None
                        }
                        image, _ = draw_detections(image, info, color=color, alpha=0.2, line_number=cnt)
                        cnt += 1
                    else:
                        continue

                # 在表格中显示过滤后的检测结果
                self.table_placeholder.table(disp_res.results_df)
            else:
                # 如果没有检测结果，显示空表格
                self.table_placeholder.table(pd.DataFrame(columns=["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)"]))

            # 调整图像尺寸
            resized_image = cv2.resize(image, (self.new_width, self.new_height))
            resized_frame = cv2.resize(frame, (self.new_width, self.new_height))

            img_name = self.logTable.saved_names[frame_id]  # 获取指定帧的图像名称

            # 根据显示模式显示处理后的图像或原始图像
            if self.display_mode == "叠加显示":
                self.image_placeholder.image(resized_image, channels="BGR", caption="识别画面: " + img_name)
            else:
                self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面: " + img_name)
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

                # 遍历检测到的对象
                for idx, info in enumerate(det_info):
                    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']

                    # Ensure cls_id is within bounds
                    if cls_id >= len(self.colors):
                        st.warning(f"⚠️ 警告: 检测到的类别索引 {cls_id} 超出颜色列表范围！使用默认颜色。")
                        color = (255, 0, 0)  # 默认红色
                    else:
                        color = self.colors[cls_id]

                    if mask is not None and self.rectangle_bounding_output:
                        # mask: numpy array, shape (H, W), values 0/1 or 0/255
                        mask_bin = (mask > 0).astype(np.uint8)
                        contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        if contours:
                            x, y, w, h = cv2.boundingRect(contours[0])
                            bbox = [x, y, x + w, y + h]
                            info['bbox'] = bbox  # 更新bbox为矩形框

                    if name in self.selected_classes:
                        # 绘制检测框、标签和面积信息
                        if not is_api:
                            image, aim_frame_area = draw_detections(image, info, color=color, alpha=0.5, line_number=cnt)
                        else:
                            image, aim_frame_area = draw_detections(image, info, alpha=0.5, line_number=cnt, is_api=True)

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
            st.header("📷 视频/图片检测系统")
            self.display_mode = st.radio("单/双画面显示设置", ["叠加显示", "对比显示"])
            self.image_placeholder = st.empty()
            self.image_placeholder_res = st.empty()
            # 根据显示模式创建用于显示视频画面的空容器
            if self.display_mode == "叠加显示":
                if not self.logTable.saved_images_ini:
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
            else:
                # "双画面显示"
                if not self.logTable.saved_images_ini:
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
                    self.image_placeholder_res.image(load_default_image(), caption="识别画面")
            # 显示用的进度条
            self.progress_bar = st.progress(0)

        # 创建一个空的结果表格
        res = concat_results("None", "[0, 0, 0, 0]", "0.00", "0.00s")

        # 在最右侧列设置识别结果表格的显示
        with col2:
            st.header("🖼️ 当前图片检测结果")
            self.table_placeholder = st.empty()  # 调整到最右侧显示
            self.table_placeholder.table(res)

            self.selectbox_placeholder = st.empty()

            # 初始化目标过滤选项
            idx = st.session_state.get('image_play_index', 0)

            detected_targets = st.session_state.get("select_info", ["全部目标"])
            selectbox_target = self.selectbox_placeholder.selectbox("目标过滤", detected_targets, key='selectbox_target')
            # 延迟执行 toggle_comboBox
            if 'last_target' not in st.session_state or st.session_state['last_target'] != selectbox_target:
                self.selectbox_target = selectbox_target
                st.session_state['last_target'] = selectbox_target
                self.toggle_comboBox(idx)

            # 创建一个导出结果的按钮
            st.write("---------------------")
            if st.button("📤 导出结果"):
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.saved_log_data = os.path.join(self.csv_output_path, f"log_table_data_{current_time}")

                if self.export_format == "CSV":
                    self.saved_log_data += ".csv"
                    self.logTable.save_to_csv(self.saved_log_data)
                    st.write(f"识别结果文件已经保存为 CSV 格式：{self.saved_log_data}")
                elif self.export_format == "Excel":
                    self.saved_log_data += ".xlsx"
                    self.logTable.save_to_excel(self.saved_log_data)
                    st.write(f"识别结果文件已经保存为 Excel 格式：{self.saved_log_data}")
                elif self.export_format == "JSON":
                    self.saved_log_data += ".json"
                    self.logTable.save_to_json(self.saved_log_data)
                    st.write(f"识别结果文件已经保存为 JSON 格式：{self.saved_log_data}")
                elif self.export_format == "Word":
                    self.saved_log_data += ".docx"
                    self.logTable.save_to_word(self.saved_log_data)
                    st.write(f"识别结果文件已经保存为 Word 格式：{self.saved_log_data}")

                self.logTable.clear_data()
            st.header("📜 历史日志")
            # 显示所有结果记录的空白表格
            self.log_table_placeholder = st.empty()
            self.logTable.update_table(self.log_table_placeholder)

        # 在第五列设置一个空的停止按钮占位符

        with col1:
            st.write("")
            run_button = st.button("🚀 开始检测")
            self.close_placeholder = st.empty()

            # ====== 新增：图片和视频切换显示功能 ======
            # 优先显示图片切换
            if hasattr(self.logTable, "saved_images_ini") and len(self.logTable.saved_images_ini) > 0:
                total_imgs = len(st.session_state['saved_images_ini'])
                if 'image_play_index' not in st.session_state or st.session_state['image_play_index'] >= total_imgs:
                    st.session_state['image_play_index'] = total_imgs - 1

                col_prev, col_next = st.columns([1, 1])
                with col_prev:
                    if st.button("⬅️ 上一张图片", key="prev_image"):
                        if st.session_state['image_play_index'] > 0:
                            st.session_state['image_play_index'] -= 1
                with col_next:
                    if st.button("下一张图片 ➡️", key="next_image"):
                        if st.session_state['image_play_index'] < total_imgs - 1:
                            st.session_state['image_play_index'] += 1

                # 替换这里的显示和表格更新逻辑，统一调用 toggle_comboBox 处理
                idx = st.session_state['image_play_index']
                self.toggle_comboBox(idx)
            else:
                # 如果没有保存的图像，则显示默认图像
                self.image_placeholder.image(load_default_image(), caption="原始画面")
                if self.display_mode == "对比显示" and self.image_placeholder_res:
                    self.image_placeholder_res.image(load_default_image(), caption="识别画面")

        st.header("📊 实时监控仪表盘")
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
        self.frame_count_placeholder.metric("📸 当前帧数", st.session_state['current_frame_count'])
        self.fps_placeholder.metric("⚡ 当前帧率 (FPS)", st.session_state['current_fps'])
        self.target_count_placeholder.metric("🎯 检测目标数量", st.session_state['current_target_count'])
        self.detection_time_placeholder.metric("⏱️ 检测用时 (秒)", st.session_state['current_detection_time'])

        if run_button:
            self.process_camera_or_file()  # 运行摄像头或文件处理
            st.rerun()  # 重新运行以更新界面

# 实例化并运行应用
if __name__ == "__main__":
    app = Detection_UI(from_streamlit=True)
    app.setupMainWindow()
