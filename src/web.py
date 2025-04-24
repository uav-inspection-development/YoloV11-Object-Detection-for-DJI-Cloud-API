import random
import tempfile
import time
import os
import cv2
import numpy as np
import streamlit as st
from QtFusion.path import abs_path
from QtFusion.utils import drawRectBox

from log import ResultLogger, LogTable
from model import Web_Detector
from chinese_name_list import EL_type, EL_class_colors, Thermo_type, Thermo_class_colors, Visible_type, Visible_class_colors, Segmentation_type, Segmentation_class_colors
from ui_style import def_css_html
from utils import save_uploaded_file, concat_results, load_default_image, get_camera_names, draw_detections, save_chinese_image, format_time
import tempfile
from datetime import datetime


class Detection_UI:
    """
    检测系统类。

    Attributes:
        model_type (str): 模型类型。
        conf_threshold (float): 置信度阈值。
        iou_threshold (float): IOU阈值。
        selected_camera (str): 选定的摄像头。
        file_type (str): 文件类型。
        uploaded_file (FileUploader): 上传的文件。
        detection_result (str): 检测结果。
        detection_location (str): 检测位置。
        detection_confidence (str): 检测置信度。
        detection_time (str): 检测用时。
    """

    def __init__(self, from_streamlit=False, api_params=None):
        """
        初始化智慧图像检测系统的参数。
        """
        self.from_streamlit = from_streamlit
        self.api_params = api_params or {}

        # 初始化类别标签列表和为每个类别随机分配颜色
        self.cls_name = Visible_type
        self.detect_class_color = Visible_class_colors
        self.colors = [self.detect_class_color.get(class_name, (0, 255, 0)) for class_name in self.cls_name.values()]

        # 设置页面标题
        self.title = "智慧图像识别系统"
        if self.from_streamlit:
            self.setup_page()  # 初始化页面布局
            def_css_html()  # 应用 CSS 样式

        # 初始化检测相关的配置参数
        self.model_type = "检测任务"
        self.conf_threshold = 0.15  # 默认置信度阈值
        self.iou_threshold = 0.5  # 默认IOU阈值
        self.image_type = "可见光"  # 图像类型

        # 初始化检测类别相关的配置参数
        self.available_classes = None  # 可用的检测类别
        self.selected_classes = list(self.cls_name.keys())  # 选定的检测类别

        # 初始化相机和文件相关的变量
        self.selected_camera = None
        self.file_type = None
        self.uploaded_file = None
        self.uploaded_video = None
        self.custom_model_file = None  # 自定义的模型文件

        # 初始化检测结果相关的变量
        self.detection_result = None
        self.detection_location = None
        self.detection_confidence = None
        self.detection_time = None

        # 初始化UI显示相关的变量（仅Streamlit）
        self.display_mode = None  # 设置显示模式
        self.close_flag = None  # 控制图像显示结束的标志
        self.close_placeholder = None  # 关闭按钮区域
        self.image_placeholder = None  # 用于显示图像的区域
        self.image_placeholder_res = None  # 图像显示区域
        self.table_placeholder = None  # 表格显示区域
        self.log_table_placeholder = None  # 完整结果表格显示区域
        self.selectbox_placeholder = None  # 下拉框显示区域
        self.selectbox_target = None  # 下拉框选中项
        self.progress_bar = None  # 用于显示的进度条

        # 初始化FPS和视频时间指针
        self.FPS = 30
        self.timenow = 0

        # 初始化日志数据保存路径
        self.saved_log_data = abs_path("../tempDir/log_table_data.csv", path_type="current")

        # 处理 Flask / Streamlit 的差异初始化
        
        if self.from_streamlit:
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
            # 初始化或获取识别结果的表格
            self.logTable = st.session_state['logTable']
            self.model = st.session_state['model']
        else:
            self.available_cameras = get_camera_names()
            self.logTable = LogTable(self.saved_log_data)
            self.model = Web_Detector()

        # 加载训练的模型权重
        self.model.load_model(model_path=abs_path("../weights/yolov8s.pt", path_type="current"), detect_type=self.cls_name)
        # 为模型中的类别重新分配颜色，如果没有指定颜色，则随机生成
        self.colors = [
            self.detect_class_color.get(class_name, [random.randint(0, 255) for _ in range(3)])
            for class_name in self.model.names
        ]

        if self.from_streamlit:
            self.setup_sidebar()  # 初始化侧边栏布局
        else:
            self.load_api_params()  # 加载API参数

    def load_api_params(self):
        """
        用于 Flask 模式，根据 API 提供的参数设置实例变量。
        """
        self.conf_threshold = float(self.api_params.get("conf_threshold", 0.15))
        self.iou_threshold = float(self.api_params.get("iou_threshold", 0.25))
        self.model_type = self.api_params.get("model_type", "检测任务")
        self.image_type = self.api_params.get("image_type", "可见光")
        self.selected_classes = self.api_params.get("selected_classes", list(Visible_type.keys()))

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
            else:
                self.cls_name = Visible_type
                self.detect_class_color = Visible_class_colors

        # 重新加载模型
        if self.model_type == "检测任务":
            if self.image_type == "红外":
                model_path = abs_path("../weights/yolo11s-thermo.pt", path_type="current")
            elif self.image_type == "EL隐裂":
                model_path = abs_path("../weights/yolo11s-el.pt", path_type="current")
            else:
                model_path = abs_path("../weights/yolo11s-visible.pt", path_type="current")
        else:
            if self.image_type == "红外":
                model_path = abs_path("../weights/yolo11s-thermo-seg.pt", path_type="current")
            elif self.image_type == "EL隐裂":
                model_path = abs_path("../weights/yolo11s-el-seg.pt", path_type="current")
            else:
                model_path = abs_path("../weights/yolo11s-visible-seg.pt", path_type="current")

        self.model.load_model(model_path=model_path, detect_type=self.selected_classes)

    def setup_page(self):
        """
        设置 Streamlit 页面标题和布局。
        """
        # 设置页面布局
        # st.set_page_config(
        #     page_title=self.title,
        #     page_icon="REC",
        #     initial_sidebar_state="expanded"
        # )

        # 居中显示标题
        st.markdown(
            f'<h1 style="text-align: center;">{self.title}</h1>',
            unsafe_allow_html=True
        )

    def setup_sidebar(self):
        """
        设置 Streamlit 侧边栏。

        在侧边栏中配置模型设置、摄像头选择以及识别项目设置等选项。
        """
        # 置信度阈值的滑动条
        self.conf_threshold = float(st.sidebar.slider("置信度设定", min_value=0.0, max_value=1.0, value=0.15))
        # IOU阈值的滑动条
        self.iou_threshold = float(st.sidebar.slider("IOU设定", min_value=0.0, max_value=1.0, value=0.25))
        # 设置侧边栏的模型设置部分
        st.sidebar.header("模型设置")
        # 选择模型类型的下拉菜单
        self.model_type = st.sidebar.selectbox("选择任务类型", ["检测任务", "分割任务"])

        # 添加提示信息
        if self.model_type == "检测任务":
            st.sidebar.caption("提示: 检测任务将检测异常的光伏板组件，目标类别按实际需要选择。")
        elif self.model_type == "分割任务":
            st.sidebar.caption("提示: 分割任务将对所有的光伏板轮廓进行分割，目标类别选择【太阳能板】即可。")

        # 添加图像类型选择
        st.sidebar.header("图像类型选择")
        self.image_type = st.sidebar.radio(
            "选择图像类型",
            options=["红外", "EL隐裂", "可见光"],
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
        elif self.model_type == "分割任务":
            self.cls_name = Segmentation_type
            self.detect_class_color = Segmentation_class_colors

        # 提示用户选择的图像类型
        st.sidebar.caption(f"提示: 当前选择的图像类型为: {self.image_type}")

        # 设置侧边栏的选择需要检测的目标类别部分，默认选择所有类别
        st.sidebar.header("目标类别选择")
        self.available_classes = list(self.cls_name.values())
        self.selected_classes = st.sidebar.multiselect(
            "选择需要检测或分割的目标类别",
            options=self.available_classes,
            default=self.available_classes  # 默认选择所有类别
        )

        # 添加提示信息
        if len(self.selected_classes) == 0:
            st.sidebar.caption("提示: 未选择任何类别，模型将不会检测任何目标。")
        else:
            st.sidebar.caption(f"提示: 当前选择的类别为: {', '.join(self.selected_classes)}")

        # Map the selected Chinese names back to their English names
        self.selected_classes = [
            english_name for english_name, chinese_name in self.cls_name.items() if chinese_name in self.selected_classes
        ]

        # 选择模型文件类型，可以是默认的或者自定义的
        model_file_option = st.sidebar.radio("模型设置", ["默认", "指定权重文件"])
        if model_file_option == "指定权重文件":
            # 如果选择自定义模型文件，则提供文件上传器
            model_file = st.sidebar.file_uploader("选择.pt文件", type="pt")

            # 如果上传了模型文件，则保存并加载该模型
            if model_file is not None:
                self.custom_model_file = save_uploaded_file(model_file)
                self.model.load_model(model_path=self.custom_model_file, detect_type=self.selected_classes)
                self.colors = [
                    self.detect_class_color.get(class_name, [random.randint(0, 255) for _ in range(3)])
                    for class_name in self.model.names
                ]
        elif model_file_option == "默认":
            if self.model_type == "检测任务":
                if self.image_type == "红外":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-thermo.pt", path_type="current"), detect_type=self.selected_classes)
                elif self.image_type == "EL隐裂":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-el.pt", path_type="current"), detect_type=self.selected_classes)
                elif self.image_type == "可见光":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-visible.pt", path_type="current"), detect_type=self.selected_classes)
            elif self.model_type == "分割任务":
                if self.image_type == "红外":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-thermo-seg.pt", path_type="current"), detect_type=self.selected_classes)
                elif self.image_type == "EL隐裂":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-el-seg.pt", path_type="current"), detect_type=self.selected_classes)
                elif self.image_type == "可见光":
                    self.model.load_model(model_path=abs_path("../weights/yolo11s-visible-seg.pt", path_type="current"), detect_type=self.selected_classes)
            # 为模型中的类别重新分配颜色
            self.colors = [
                self.detect_class_color.get(class_name, [random.randint(0, 255) for _ in range(3)])
                for class_name in self.model.names
            ]

        # 设置侧边栏的摄像头和 RTSP/RTMP 配置部分
        st.sidebar.header("摄像头和流媒体识别设置")
        # 选择输入源类型：摄像头或 RTSP/RTMP 流
        self.input_source = st.sidebar.radio("选择输入源", ["摄像头", "RTSP/RTMP流"])

        if self.input_source == "摄像头":
            # 选择摄像头的下拉菜单
            self.selected_camera = st.sidebar.selectbox("选择摄像头序号", self.available_cameras)
        elif self.input_source == "RTSP/RTMP流":
            # 输入 RTSP/RTMP 地址
            self.rtsp_rtmp_url = st.sidebar.text_input("输入RTSP/RTMP地址", placeholder="例如：rtsp://<ip>:<port>/path 或 rtmp://<ip>:<port>/path")

        # 添加视频输出和 RTSP 输出的启用复选框
        st.sidebar.header("输出设置")
        self.enable_video_output = st.sidebar.checkbox("启用视频输出", value=True)

        st.sidebar.write("选择输出文件路径：")
        self.output_path = st.sidebar.text_input("输出文件路径", value="./output", placeholder="例如：./output 或 D:/videos")

        self.enable_rtsp_output = st.sidebar.checkbox("启用RTSP/RTMP输出", value=False)

        # RTSP/RTMP输出地址输入
        if self.enable_rtsp_output:
            st.sidebar.write("设置RTSP/RTMP输出地址：")
            self.rtsp_output_url = st.sidebar.text_input("RTSP/RTMP输出地址", placeholder="例如：rtmp://<ip>:<port>/live/stream 或 rtsp://<ip>:<port>/path")

        # 设置侧边栏的识别项目设置部分
        st.sidebar.header("图片视频识别设置")
        # 选择文件类型的下拉菜单
        self.file_type = st.sidebar.selectbox("选择文件类型", ["图片文件", "视频文件"])
        # 根据所选的文件类型，提供对应的文件上传器
        if self.file_type == "图片文件":
            self.uploaded_file = st.sidebar.file_uploader("上传图片", type=["jpg", "png", "jpeg"])
        elif self.file_type == "视频文件":
            self.uploaded_video = st.sidebar.file_uploader("上传视频文件", type=["mp4"])

        # 提供相关提示信息，根据所选摄像头和文件类型的不同情况
        if self.selected_camera == "摄像头检测关闭" or self.rtsp_rtmp_url == "":
            if self.file_type == "图片文件":
                st.sidebar.write("请选择图片并点击'开始运行'按钮，进行图片检测！")
            if self.file_type == "视频文件":
                st.sidebar.write("请选择视频并点击'开始运行'按钮，进行视频检测！")
        else:
            st.sidebar.write("请点击'开始检测'按钮，启动摄像头检测！")

    def load_model_file(self):
        if self.custom_model_file:
            self.model.load_model(self.custom_model_file)
        else:
            pass  # 载入

    def process_camera_or_file(self):
        """
        处理摄像头、RTSP/RTMP流或文件输入。

        根据用户选择的输入源（摄像头、图片文件、视频文件或RTSP/RTMP流），处理并显示检测结果。
        """
        # 如果选择了摄像头输入
        if self.input_source == "摄像头" and self.selected_camera != "摄像头检测关闭" or self.input_source == "RTSP/RTMP流":
            if self.input_source == "摄像头":
                input_type = "camera"
                # 使用 OpenCV 捕获摄像头画面
                if str(self.selected_camera) == '0':
                    input_source = 0
                else:
                    if len(self.selected_camera) < 8:
                        input_source = int(self.selected_camera)
                    else:
                        input_source = self.selected_camera
            elif self.input_source == "RTSP/RTMP流":
                input_type = "stream"
                if not self.rtsp_rtmp_url:
                    st.warning("请输入有效的RTSP/RTMP地址！")
                    return
                input_source = self.rtsp_rtmp_url
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
                        # 调节摄像头的分辨率
                        # 设置新的尺寸
                        new_width = 1080
                        new_height = int(new_width * (9 / 16))
                        # 调整图像尺寸
                        frame = cv2.resize(frame, (new_width, new_height))


                        framecopy = frame.copy()
                        image, detInfo, _ = self.frame_process(frame, input_type)

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

                        # 设置新的尺寸
                        new_width = 1080
                        new_height = int(new_width * (9 / 16))
                        # 调整图像尺寸
                        resized_image = cv2.resize(image, (new_width, new_height))
                        resized_frame = cv2.resize(framecopy, (new_width, new_height))
                        if self.display_mode == "叠加显示":
                            self.image_placeholder.image(resized_image, channels="BGR", caption="视频画面")
                        else:
                            self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面")
                            self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面")

                        self.logTable.add_frames(image, detInfo, cv2.resize(frame, (640, 640)))

                        # 更新进度条
                        progress_percentage = int((current_frame / total_frames) * 100)
                        self.progress_bar.progress(progress_percentage)
                        current_frame = (current_frame + 1) % total_frames  # 重置进度条
                    else:
                        break
                if self.close_flag:
                    self.logTable.save_to_csv()
                    self.logTable.update_table(self.log_table_placeholder)
                    cap.release()
                    if self.enable_video_output:
                        video_out.release()
                    if self.enable_rtsp_output:
                        stream_out.release()

                self.logTable.save_to_csv()
                self.logTable.update_table(self.log_table_placeholder)
                cap.release()
                if self.enable_video_output:
                    video_out.release()
                if self.enable_rtsp_output:
                    stream_out.release()


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

                res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in)
                st.write("识别结果文件已经保存：" + self.saved_log_data)
                if res:
                    st.write(f"结果的目标文件已经保存：{res}")


        else:
            # 如果上传了图片文件
            if self.uploaded_file is not None:
                # output/image/xxx.avi

                self.logTable.clear_frames()
                self.progress_bar.progress(0)
                # 显示上传的图片
                source_img = self.uploaded_file.read()
                file_bytes = np.asarray(bytearray(source_img), dtype=np.uint8)
                image_ini = cv2.imdecode(file_bytes, 1)
                framecopy = image_ini.copy()
                image, detInfo, select_info = self.frame_process(image_ini, self.uploaded_file.name)
                save_chinese_image(self.output_path + '/image/' + self.uploaded_file.name, image)
                # self.selectbox_placeholder = st.empty()
                # self.selectbox_target = self.selectbox_placeholder.selectbox("目标过滤", select_info, key="22113")

                self.logTable.save_to_csv()
                self.logTable.update_table(self.log_table_placeholder)  # 更新所有结果记录的表格

                # 设置新的尺寸
                new_width = 1080
                new_height = int(new_width * (9 / 16))
                # 调整图像尺寸
                resized_image = cv2.resize(image, (new_width, new_height))
                resized_frame = cv2.resize(framecopy, (new_width, new_height))
                if self.display_mode == "叠加显示":
                    self.image_placeholder.image(resized_image, channels="BGR", caption="图片显示")
                else:
                    self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面")
                    self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面")

                self.logTable.add_frames(image, detInfo, cv2.resize(image_ini, (640, 640)))
                self.progress_bar.progress(100)

            # 如果上传了视频文件
            elif self.uploaded_video is not None:
                # output/video_name/video/xxx.avi
                # output/video_name/image/xxx.jpg

                # 处理上传的视频
                self.logTable.clear_frames()
                self.close_flag = self.close_placeholder.button(label="停止")

                video_file = self.uploaded_video
                tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
                try:
                    tfile.write(video_file.read())
                    tfile.flush()

                    tfile.seek(0)  # 确保文件指针回到文件开头

                    cap = cv2.VideoCapture(tfile.name)

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
                            framecopy = frame.copy()
                            # 计算当前帧对应的时间（秒）
                            current_time = current_frame / fps
                            if current_time < total_length:
                                current_frame += 1
                                current_time_str = format_time(current_time)
                                image, detInfo, _ = self.frame_process(frame, self.uploaded_video.name, video_time=current_time_str)
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

                                # 设置新的尺寸
                                new_width = 1080
                                new_height = int(new_width * (9 / 16))
                                # 调整图像尺寸
                                resized_image = cv2.resize(image, (new_width, new_height))
                                resized_frame = cv2.resize(framecopy, (new_width, new_height))
                                if self.display_mode == "叠加显示":
                                    self.image_placeholder.image(resized_image, channels="BGR", caption="视频画面")
                                else:
                                    self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面")
                                    self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面")

                                self.logTable.add_frames(image, detInfo, cv2.resize(frame, (640, 640)))

                                # 更新进度条
                                if total_length > 0:
                                    progress_percentage = int(((current_frame + 1) / total_frames) * 100)
                                    try:
                                        self.progress_bar.progress(progress_percentage)
                                    except:
                                        pass

                                current_frame += 1
                        else:
                            break
                    if self.close_flag:
                        self.logTable.save_to_csv()
                        self.logTable.update_table(self.log_table_placeholder)
                        cap.release()
                        if self.enable_video_output:
                            video_out.release()

                    self.logTable.save_to_csv()
                    self.logTable.update_table(self.log_table_placeholder)
                    cap.release()
                    if self.enable_video_output:
                        video_out.release()

                finally:
                    cap.release()
                    if self.enable_video_output:
                        video_out.release()

                    if self.uploaded_video is None:
                        name_in = None
                    else:
                        name_in = self.uploaded_video.name

                    res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in)
                    st.write("识别结果文件已经保存：" + self.saved_log_data)
                    if res:
                        st.write(f"结果的目标文件已经保存：{res}")

                    tfile.close()
                    # 如果不需要再保留临时文件，可以在处理完后删除
                    print(tfile.name + ' 临时文件可以删除')
                    # os.remove(tfile.name)

            else:
                st.warning("请选择摄像头或上传文件。")

    def toggle_comboBox(self, frame_id):
        """
        处理并显示指定帧的检测结果。

        Args:
            frame_id (int): 指定要显示检测结果的帧ID。

        根据用户选择的帧ID，显示该帧的检测结果和图像。
        """
        # 确保已经保存了检测结果
        if len(self.logTable.saved_results) > 0:
            frame = self.logTable.saved_images_ini[-1]  # 获取最近一帧的图像
            image = frame  # 将其设为当前图像

            # 遍历所有保存的检测结果
            for i, detInfo in enumerate(self.logTable.saved_results):
                if frame_id != -1:
                    # 如果指定了帧ID，只处理该帧的结果
                    if frame_id != i:
                        continue

                if len(detInfo) > 0:
                    name, bbox, conf, use_time, cls_id = detInfo  # 获取检测信息
                    label = '%s %.0f%%' % (name, conf * 100)  # 构造标签文本

                    disp_res = ResultLogger()  # 创建结果记录器
                    res = disp_res.concat_results(name, bbox, str(round(conf, 2)), str(use_time))  # 合并结果
                    self.table_placeholder.table(res)  # 在表格中显示结果

                    # 如果有保存的初始图像
                    if len(self.logTable.saved_images_ini) > 0:
                        if len(self.colors) < cls_id:
                            # 拓展颜色列表以适应当前类别ID
                            self.colors.extend(
                                [[random.randint(0, 255) for _ in range(3)] for _ in range(cls_id + 1 - len(self.colors))]
                            )
                        image = drawRectBox(image, bbox, alpha=0.2, addText=label,
                                            color=self.colors[cls_id])  # 绘制检测框和标签

            # 设置新的尺寸并调整图像尺寸
            new_width = 1080
            new_height = int(new_width * (9 / 16))
            resized_image = cv2.resize(image, (new_width, new_height))
            resized_frame = cv2.resize(frame, (new_width, new_height))

            # 根据显示模式显示处理后的图像或原始图像
            if self.display_mode == "叠加显示":
                self.image_placeholder.image(resized_image, channels="BGR", caption="识别画面")
            else:
                self.image_placeholder.image(resized_frame, channels="BGR", caption="原始画面")
                self.image_placeholder_res.image(resized_image, channels="BGR", caption="识别画面")

    def frame_process(self, image, file_name,video_time = None):
        """
        处理并预测单个图像帧的内容。

        Args:
            image (numpy.ndarray): 输入的图像。
            file_name (str): 处理的文件名。

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

        aim_area = 0 #计算目标面积

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
                for info in det_info:
                    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']

                    if name in self.selected_classes:
                        # 绘制检测框、标签和面积信息
                        image, aim_frame_area = draw_detections(image, info, alpha=0.5)
                        # image = drawRectBox(image, bbox, alpha=0.2, addText=label, color=self.colors[cls_id])

                        res = disp_res.concat_results(name, bbox, str(int(aim_frame_area)),
                                                    video_time if video_time is not None else str(round(use_time, 2)))

                        # 添加日志条目
                        self.logTable.add_log_entry(file_name, name, bbox, int(aim_frame_area), video_time if video_time is not None else str(round(use_time, 2)))
                        # 记录检测信息
                        detInfo.append([name, bbox, int(aim_frame_area), video_time if video_time is not None else str(round(use_time, 2)), cls_id])
                        # 添加到选择信息列表
                        select_info.append(name + "-" + str(cnt))
                        cnt += 1

                # 在表格中显示检测结果
                self.table_placeholder.table(res)

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
        # st.title(self.title) # 显示系统标题
        st.write("--------")
        st.write("光伏云组件检测系统")
        st.write("--------")
        # 插入一条分割线

        # 创建列布局，将表格移到最右侧
        col1, col2, col3 = st.columns([4, 1, 2])

        # 在第一列设置显示模式的选择
        with col1:
            self.display_mode = st.radio("单/双画面显示设置", ["叠加显示", "对比显示"])
            # 根据显示模式创建用于显示视频画面的空容器
            if self.display_mode == "叠加显示":
                self.image_placeholder = st.empty()
                if not self.logTable.saved_images_ini:
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
            else:
                # "双画面显示"
                self.image_placeholder = st.empty()
                self.image_placeholder_res = st.empty()
                if not self.logTable.saved_images_ini:
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
                    self.image_placeholder_res.image(load_default_image(), caption="识别画面")
            # 显示用的进度条
            self.progress_bar = st.progress(0)

        # 创建一个空的结果表格
        res = concat_results("None", "[0, 0, 0, 0]", "0.00", "0.00s")

        # 在最右侧列设置识别结果表格的显示
        with col3:
            self.table_placeholder = st.empty()  # 调整到最右侧显示
            self.table_placeholder.table(res)

            # 创建一个导出结果的按钮
            st.write("---------------------")
            if st.button("导出结果"):
                self.logTable.save_to_csv()
                if self.uploaded_video is None:
                    name_in = None
                else:
                    name_in = self.uploaded_video.name
                res = self.logTable.save_frames_file(fps=self.FPS, video_name=name_in)
                st.write("识别结果文件已经保存：" + self.saved_log_data)
                if res:
                    st.write(f"结果的目标文件已经保存：{res}")
                self.logTable.clear_data()
            # 显示所有结果记录的空白表格
            self.log_table_placeholder = st.empty()
            self.logTable.update_table(self.log_table_placeholder)

        # 在第五列设置一个空的停止按钮占位符
        with col2:
            st.write("")
            self.close_placeholder = st.empty()

        # 在第二列处理目标过滤
        # with col2:
        # self.selectbox_placeholder = st.empty()
        # detected_targets = ["全部目标"] # 初始化目标列表
        #
        # 遍历并显示检测结果
        # for i, info in enumerate(self.logTable.saved_results):
        # name, bbox, conf, use_time, cls_id = info
        # detected_targets.append(name + "-" + str(i))
        # self.selectbox_target = self.selectbox_placeholder.selectbox("目标过滤", detected_targets)
        #
        # 处理目标过滤的选择
        # for i, info in enumerate(self.logTable.saved_results):
        # name, bbox, conf, use_time, cls_id = info
        # if self.selectbox_target == name + "-" + str(i):
        # self.toggle_comboBox(i)
        # elif self.selectbox_target == "全部目标":
        # self.toggle_comboBox(-1)

        with col2:
            st.write("")
            run_button = st.button("开始检测")
            if run_button:
                self.process_camera_or_file()  # 运行摄像头或文件处理
            else:
                # 如果没有保存的图像，则显示默认图像
                if not self.logTable.saved_images_ini:
                    self.image_placeholder.image(load_default_image(), caption="原始画面")
                    if self.display_mode == "对比显示":
                        self.image_placeholder_res.image(load_default_image(), caption="识别画面")


# 实例化并运行应用
if __name__ == "__main__":
    app = Detection_UI(from_streamlit=True)
    app.setupMainWindow()
