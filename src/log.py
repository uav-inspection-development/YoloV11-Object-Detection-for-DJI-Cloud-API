import os
import time
import cv2
import traceback
import pandas as pd
from pathlib import Path
from QtFusion.path import abs_path
from PIL import Image
import numpy as np
from datetime import datetime
from docx import Document
from docx.shared import Inches
from io import BytesIO
from utils import extract_gps_info, format_gps_info
from naming_config import (
    get_system_default,
    get_table_column,
    get_system_message,
    get_gps_message,
    get_report_field,
    get_fault_category,
    get_report_statistic,
    get_report_table_header
)


def save_chinese_image(file_path, image_array):
    """
    保存带有中文路径的图片文件

    参数：
    file_path (str): 图片的保存路径，应包含中文字符, 例如 '示例路径/含有中文的文件名.png'
    image_array (numpy.ndarray): 要保存的 OpenCV 图像（即 numpy 数组）
    """
    try:
        # 将 OpenCV 图片转换为 Pillow Image 对象
        image = Image.fromarray(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))

        # 使用 Pillow 保存图片文件
        image.save(file_path)

        print(f"{get_system_message('save_image_success').format(path=file_path)}")
    except Exception as e:
        print(f"{get_system_message('save_image_failed').format(error=str(e))}")


class ResultLogger:
    def __init__(self):
        """
        初始化ResultLogger类。
        """
        self.results_df = pd.DataFrame(columns=[
            get_table_column("detection_result"),
            get_table_column("type"),
            get_table_column("location"),
            get_table_column("area"),
            get_table_column("time")
        ])

    def concat_results(self, result, chinese_name, location, confidence, time):
        """
        显示检测结果，并将结果添加到结果DataFrame中。

        Args:
            result (str): 检测结果。
            chinese_name (str): 中文结果
            location (str): 检测位置。
            confidence (str): 置信度。
            time (str): 检出目标所在时间。

        Returns:
            pd.DataFrame: 更新后的DataFrame。
        """
        # 创建一个包含这些信息的字典
        result_data = {
            get_table_column("detection_result"): [result],
            get_table_column("type"): [chinese_name],
            get_table_column("location"): [location],
            get_table_column("area"): [confidence],
            get_table_column("time"): [time]
        }

        # 创建一个新的DataFrame并将其添加到实例的DataFrame
        new_row = pd.DataFrame(result_data)
        self.results_df = pd.concat([self.results_df, new_row], ignore_index=True)

        return self.results_df


class LogTable:
    def __init__(self, csv_file_path=None):
        """
        初始化类实例。

        Args:
            csv_file_path (str): 保存初始数据的CSV文件路径。
        """
        self.csv_file_path = csv_file_path
        self.saved_images = []
        self.saved_target_images = []
        self.saved_images_ini = []
        self.saved_results = []
        self.saved_names = []
        self.saved_targets_info = []  # 存储每张图片的目标类别信息
        self.saved_image_paths = []  # 存储原始图片路径，用于GPS信息解析

        self.columns = [
            get_table_column("file_path"),
            get_table_column("detection_result"),
            get_table_column("type"),
            get_table_column("location"),
            get_table_column("area"),
            get_table_column("time")
        ]
        self.data = pd.DataFrame(columns=self.columns)

    def add_frames(self, image, detInfo, img_ini, img_name=None, img_path=None):
        """
        将检测到的图像和检测信息添加到列表中。

        Args:
            image (numpy.ndarray): 检测到的图像。
            detInfo (list): 检测信息。
            img_ini (numpy.ndarray): 初始图像。
            img_name (str): 图像名称。
            img_path (str): 原始图像路径，用于GPS信息解析。
        """
        self.saved_images.append(image)
        self.saved_images_ini.append(img_ini)
        self.saved_results.append(detInfo)
        self.saved_names.append(img_name)
        self.saved_image_paths.append(img_path)  # 保存原始图片路径

        # 提取并保存当前图片的目标类别信息
        current_targets = []  # 默认为空列表
        if detInfo:
            self.saved_target_images.append(image)
            # 从detInfo中提取中文类别名称
            for det in detInfo:
                if len(det) >= 2:  # det格式: [name, chinese_name, bbox, area, time, cls_id]
                    chinese_name = det[1]  # 中文名称
                    if chinese_name not in current_targets:
                        current_targets.append(chinese_name)

        self.saved_targets_info.append(current_targets)
        # print('____')
        # print(detInfo)
        # print('____')

    def clear_frames(self):
        """
        清空保存的图像和检测信息列表。
        """
        self.saved_images = []
        self.saved_images_ini = []
        self.saved_results = []
        self.saved_target_images = []
        self.saved_names = []
        self.saved_targets_info = []
        self.saved_image_paths = []

    def save_frames_file(self, fps=30, video_name='save', video_time=None, output_path='output/frame/'):
        """
        保存检测到的图像和视频文件。

        Args:
            fps (int): 视频的帧率。
            video_name (str): 视频文件的名称。
            video_time (str): 视频时间戳。
            output_path (str): 输出路径。
        """
        if self.saved_images:  # 检查列表是否不为空
            # 执行保存操作
            now_time = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime(time.time()))
            if len(self.saved_images) == 1:
                # 只有一张图像时，保存为图片
                file_name = abs_path(output_path + '/pic_' + str(now_time) + '.png', path_type="current")
                cv2.imwrite(file_name, self.saved_images[0])
                return file_name
            else:
                # 为图像序列时，保存为视频
                height, width, layers = self.saved_images[0].shape
                size = (width, height)
                if video_name is None:
                    save_name = 'camera'
                else:
                    save_name = video_name

                file_name = abs_path(output_path + str(save_name) + '.avi', path_type="current")

                out = cv2.VideoWriter(file_name, cv2.VideoWriter_fourcc(*'DIVX'), fps, size)
                for img in self.saved_images:
                    out.write(img)
                out.release()

                # # 保存视频和摄像头目标截图
                # if video_name is None:
                #     camera_savepath = output_path + '/camera'
                #     if not os.path.exists(camera_savepath):
                #         os.makedirs(camera_savepath)
                #
                #     try:
                #         for imgid in range(len(self.saved_target_images)):
                #             file_name = abs_path(camera_savepath + '/' + str(imgid + 1) + '.jpg', path_type="current")
                #             # cv2.imwrite(file_name, self.saved_target_images[imgid])
                #             save_chinese_image(file_name, self.saved_target_images[imgid])
                #     except:
                #         pass
                # else:
                #     video_savepath = output_path + video_name
                #     if not os.path.exists(video_savepath):
                #         os.makedirs(video_savepath)
                #
                #     try:
                #         for imgid in range(len(self.saved_target_images)):
                #             # 将字符串转换为 datetime 对象
                #             time_obj = datetime.strptime(video_time, "%H:%M:%S")
                #
                #             # 将 datetime 对象格式化为所需的字符串格式
                #             formatted_time = time_obj.strftime("%H_%M_%S")
                #             file_name = abs_path(video_savepath + '/' + formatted_time + '_' + str(imgid + 1) + '.jpg', path_type="current")
                #             # cv2.imwrite(file_name, self.saved_target_images[imgid])
                #             save_chinese_image(file_name, self.saved_target_images[imgid])
                #     except:
                #         pass

                return file_name
        return False

    def add_log_entry(self, file_path, recognition_result, chinese_nam, position, confidence, time_spent):
        """
        向日志中添加一条新记录。

        Args:
            file_path (str): 文件路径
            recognition_result (str): 识别结果
            position (str): 位置
            confidence (float): 置信度
            time_spent (float): 用时（通常是秒或毫秒）

        Returns:
            None
        """
        # 创建新的数据行
        recognition_result = str(recognition_result)
        position_str = str(position)
        file_path = str(file_path)
        new_entry = pd.DataFrame([[file_path, recognition_result, chinese_nam, position_str, confidence, time_spent]],
                                 columns=self.columns)

        # 将新行添加到DataFrame中
        self.data = pd.concat([self.data, new_entry]).reset_index(drop=True)

        return self.data

    def clear_data(self):
        """
        清空数据表格。
        """
        self.data = pd.DataFrame(columns=self.columns)

    def save_to_csv(self, csv_file_path):
        """
        将数据保存到CSV文件。

        Args:
            csv_file_path (str): CSV文件的路径。
        """
        # 如果文件不存在，创建文件并写入表头
        if not os.path.exists(csv_file_path):
            empty_df = pd.DataFrame(columns=self.columns)
            empty_df.to_csv(csv_file_path, index=False, encoding='utf-8', mode='w', header=True)

        # 将更新后的DataFrame保存到CSV文件
        self.data.to_csv(csv_file_path, index=False, encoding='utf-8', mode='a', header=False)

    def save_to_excel(self, excel_file_path):
        """
        将数据保存到Excel文件。

        Args:
            excel_file_path (str): Excel文件的路径。
        """
        # 如果文件不存在，创建文件并写入表头
        if not os.path.exists(excel_file_path):
            empty_df = pd.DataFrame(columns=self.columns)
            empty_df.to_excel(excel_file_path, index=False, engine='openpyxl')

        # 将DataFrame保存到Excel文件
        self.data.to_excel(excel_file_path, index=False, engine='openpyxl')

    def save_to_json(self, json_file_path):
        """
        将数据保存到JSON文件。

        Args:
            json_file_path (str): JSON文件的路径。
        """
        # 将DataFrame保存到JSON文件
        self.data.to_json(json_file_path, orient='records', lines=True, force_ascii=False)

    def save_to_word(self, word_file_path, detection_params=None):
        """
        将检测结果保存到专业的无人机光伏巡检报告格式的 Word 文件。

        Args:
            word_file_path (str): Word 文件的路径。
            detection_params (dict): 检测参数，包含模型类型、图像类型、置信度等
        """
        try:
            # 解析检测参数
            if detection_params is None:
                detection_params = {}

            model_type = detection_params.get('model_type', get_system_default('model_type_detection'))
            image_type = detection_params.get('image_type', get_system_default('image_type_other'))
            conf_threshold = detection_params.get('conf_threshold', 0.15)
            iou_threshold = detection_params.get('iou_threshold', 0.25)
            selected_classes = detection_params.get('selected_classes', [])
            cls_name = detection_params.get('cls_name', {})
            enable_gps_parsing = detection_params.get('enable_gps_parsing', False)

            # 创建一个 Word 文档
            doc = Document()

            # 设置页面格式
            sections = doc.sections
            for section in sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1.25)
                section.right_margin = Inches(1.25)

            # 第一页：报告标题和日期
            now = datetime.now()
            report_time = now.strftime("%Y/%m/%d %H:%M:%S")

            # 添加多个空行使标题居中
            for _ in range(8):
                doc.add_paragraph("")

            title_para = doc.add_paragraph()
            title_run = title_para.add_run(get_report_field("report_title"))
            title_run.font.size = Inches(0.25)  # 大标题
            title_run.bold = True
            title_para.alignment = 1  # 居中

            # 添加空行
            for _ in range(3):
                doc.add_paragraph("")

            date_para = doc.add_paragraph()
            date_run = date_para.add_run(report_time)
            date_run.font.size = Inches(0.15)
            date_para.alignment = 1  # 居中

            # 添加空行
            for _ in range(2):
                doc.add_paragraph("")

            # 报告编号
            report_num = f"PV-{now.strftime('%Y%m%d%H%M%S')}"
            report_num_para = doc.add_paragraph(f"{get_report_field('report_number').format(number=report_num)}")
            report_num_para.alignment = 1  # 居中

            # 第一页结束，插入分页符进入目录页
            doc.add_page_break()

            # 第二页：目录页
            toc_title = doc.add_heading(get_report_field("table_of_contents"), level=1)
            toc_title.alignment = 1  # 居中

            # 添加空行
            doc.add_paragraph("")

            # 目录内容，使用表格格式实现点线对齐
            toc_table = doc.add_table(rows=5, cols=2)
            toc_table.style = 'Light List'

            # 目录项
            toc_items = [
                (get_report_field("overview_section"), "3"),
                (get_report_field("fault_suggestion_section"), "4"),
                (get_report_field("statistics_section"), "5"),
                (get_report_field("detailed_results_section"), "6"),
                ("", "")  # 空行
            ]

            for i, (item, page) in enumerate(toc_items):
                if item:  # 非空行
                    toc_table.cell(i, 0).text = item
                    toc_table.cell(i, 1).text = page
                    toc_table.cell(i, 1).paragraphs[0].alignment = 2  # 右对齐页码

            # 目录页结束，插入分页符进入正文
            doc.add_page_break()

            # 1、概述部分
            doc.add_heading(get_report_field("overview_section"), level=1)
            overview_table = doc.add_table(rows=9, cols=2)  # 增加一行用于显示检测类别
            overview_table.style = 'Table Grid'

            # 根据检测类型和图像类型生成检测场景描述
            scene_desc = f"{image_type}{model_type}"
            if model_type == get_system_default("model_type_segmentation"):
                scene_desc += f" - {get_report_field('segmentation_description').format(image_type=image_type)}"
            else:
                scene_desc += f" - {get_report_field('detection_description').format(image_type=image_type)}"

            # 生成检测类别信息
            detection_classes = get_system_default('all_classes')  # 默认值
            if selected_classes and cls_name:
                # 将英文类别名称转换为中文
                chinese_classes = []
                for class_name in selected_classes:
                    if class_name in cls_name:
                        chinese_classes.append(cls_name[class_name])
                    else:
                        chinese_classes.append(class_name)  # 如果没有对应的中文名称，使用原名称
                detection_classes = ', '.join(chinese_classes) if chinese_classes else get_system_default('all_classes')
            elif selected_classes:
                detection_classes = ', '.join(selected_classes)

            # 概述表格数据
            overview_data = [
                [get_report_field("user_organization"), get_report_field("power_station")],
                [get_report_field("detection_scene"), scene_desc],
                [get_report_field("detection_type"), f"{model_type} - {image_type}"],
                [get_report_field("detection_classes"), detection_classes],
                [get_report_field("flight_batch"), f"UAV-{now.strftime('%Y%m%d')}"],
                [get_report_field("task_name"), f"{get_report_field('pv_inspection_task')}-{now.strftime('%Y%m%d')}"],
                [get_report_field("report_date"), report_time],
                [get_report_field("image_count"), str(len(self.saved_images))],
                [get_report_field("detection_params"), get_report_field("confidence_iou_format").format(confidence=conf_threshold, iou=iou_threshold)]
            ]

            for i, (key, value) in enumerate(overview_data):
                overview_table.cell(i, 0).text = key
                overview_table.cell(i, 1).text = value

            doc.add_paragraph("")

            # 概述部分结束，插入分页符进入故障建议部分
            doc.add_page_break()

            # 2、光伏电站故障维修建议
            doc.add_heading(get_report_field("fault_suggestion_section"), level=1)

            # 根据检测类型定义不同的故障分类
            if image_type == get_system_default("image_type_el"):
                fault_categories = {
                    get_fault_category("level_1_fault"): {
                        get_fault_category("scratch"): get_fault_category("scratch_suggestion"),
                        get_fault_category("black_chip"): get_fault_category("black_chip_suggestion")
                    },
                    get_fault_category("level_2_fault"): {
                        get_fault_category("crack"): get_fault_category("crack_suggestion"),
                        get_fault_category("fragment"): get_fault_category("fragment_suggestion"),
                        get_fault_category("corner_damage"): get_fault_category("corner_damage_suggestion")
                    }
                }
            elif image_type == get_system_default("image_type_thermal"):
                fault_categories = {
                    get_fault_category("level_1_fault"): {
                        get_fault_category("sun_reflection"): get_fault_category("sun_reflection_suggestion"),
                        get_fault_category("normal_thermal"): get_fault_category("normal_thermal_suggestion")
                    },
                    get_fault_category("level_2_fault"): {
                        get_fault_category("single_hotspot"): get_fault_category("single_hotspot_suggestion"),
                        get_fault_category("abnormal_low_temp"): get_fault_category("abnormal_low_temp_suggestion"),
                        get_fault_category("single_hotspot_low_temp"): get_fault_category("single_hotspot_low_temp_suggestion")
                    },
                    get_fault_category("level_3_fault"): {
                        get_fault_category("large_hotspot"): get_fault_category("large_hotspot_suggestion"),
                        get_fault_category("diode_short"): get_fault_category("diode_short_suggestion"),
                        get_fault_category("large_hotspot_low_temp"): get_fault_category("large_hotspot_low_temp_suggestion"),
                        get_fault_category("single_hotspot_diode_short"): get_fault_category("single_hotspot_diode_short_suggestion"),
                        get_fault_category("diode_short_low_temp"): get_fault_category("diode_short_low_temp_suggestion")
                    }
                }
            elif image_type == get_system_default("image_type_visible"):
                fault_categories = {
                    get_fault_category("level_1_fault"): {
                        get_fault_category("dirty"): get_fault_category("dirty_suggestion"),
                        get_fault_category("bird_dropping"): get_fault_category("bird_dropping_suggestion"),
                        get_fault_category("snow"): get_fault_category("snow_suggestion"),
                        get_fault_category("visible_sun_reflection"): get_fault_category("visible_sun_reflection_suggestion"),
                        get_fault_category("dirty_bird_dropping"): get_fault_category("dirty_bird_dropping_suggestion")
                    },
                    get_fault_category("level_2_fault"): {
                        get_fault_category("occlusion"): get_fault_category("occlusion_suggestion"),
                        get_fault_category("visible_crack"): get_fault_category("visible_crack_suggestion"),
                        get_fault_category("occlusion_dirty"): get_fault_category("occlusion_dirty_suggestion"),
                        get_fault_category("occlusion_bird_dropping"): get_fault_category("occlusion_bird_dropping_suggestion")
                    },
                    get_fault_category("level_3_fault"): {
                        get_fault_category("panel_crack"): get_fault_category("panel_crack_suggestion"),
                        get_fault_category("panel_missing"): get_fault_category("panel_missing_suggestion"),
                        get_fault_category("panel_deformation"): get_fault_category("panel_deformation_suggestion")
                    }
                }
            else:
                # 默认故障分类（其他类型或分割任务）
                fault_categories = {
                    get_fault_category("detection_info"): {
                        get_fault_category("person"): get_fault_category("person_suggestion"),
                        get_fault_category("vehicle"): get_fault_category("vehicle_suggestion")
                    }
                } if model_type == get_system_default("model_type_segmentation") or image_type == get_system_default('image_type_other') else {
                    get_fault_category("level_1_fault"): {
                        get_fault_category("single_component"): get_fault_category("single_component_suggestion"),
                        get_fault_category("component_string"): get_fault_category("component_string_suggestion"),
                    }
                }

            # 收集实际检测到的故障类型
            detected_faults = set()
            for detection_results in self.saved_results:
                for detInfo in detection_results:
                    if isinstance(detInfo, list) and len(detInfo) >= 2:
                        fault_type = detInfo[1]  # 中文名称
                        detected_faults.add(fault_type)

            # 输出故障建议
            for level, faults in fault_categories.items():
                doc.add_heading(level, level=2)
                for fault_name, suggestion in faults.items():
                    if any(fault_name in detected_fault for detected_fault in detected_faults):
                        doc.add_paragraph(f"{fault_name}: {suggestion}")

            doc.add_paragraph("")

            # 故障建议部分结束，插入分页符进入统计部分
            doc.add_page_break()

            # 3、结果统计
            doc.add_heading(get_report_field("statistics_section"), level=1)

            # 统计信息
            total_detections = sum(len(results) for results in self.saved_results)
            fault_counts = {}
            for detection_results in self.saved_results:
                for detInfo in detection_results:
                    if isinstance(detInfo, list) and len(detInfo) >= 2:
                        fault_type = detInfo[1]
                        fault_counts[fault_type] = fault_counts.get(fault_type, 0) + 1

            # 算法引擎描述
            if model_type == get_system_default("model_type_segmentation"):
                doc.add_paragraph(get_report_statistic("comprehensive_analysis"))
                algorithm_desc = get_report_statistic("yolo_segmentation_desc").format(type=image_type)
            else:
                doc.add_paragraph(get_report_statistic("comprehensive_detection"))
                algorithm_desc = get_report_statistic("yolo_detection_desc").format(type=image_type)

            engines = list(fault_counts.keys()) if fault_counts else [get_report_statistic("no_anomalies")]
            doc.add_paragraph(get_report_statistic("algorithm_engine").format(type=algorithm_desc))
            doc.add_paragraph(get_report_statistic("detected_categories").format(list=', '.join(engines)))

            # 添加检测类别信息
            doc.add_paragraph(get_report_statistic("configured_detection_classes").format(classes=detection_classes))
            doc.add_paragraph("")

            # 报警次数统计
            if total_detections > 0:
                doc.add_paragraph(get_report_statistic("alarm_details").format(count=total_detections))
                for fault_type, count in fault_counts.items():
                    doc.add_paragraph(get_report_statistic("fault_count_format").format(type=fault_type, count=count))
            else:
                doc.add_paragraph(get_report_statistic("alarm_count_zero"))

            doc.add_paragraph("")

            # 检测类型总统计表
            if fault_counts:
                doc.add_paragraph(get_report_statistic("detection_type_statistics"))
                stats_table = doc.add_table(rows=1, cols=4)
                stats_table.style = 'Table Grid'
                headers = [
                    get_report_table_header("detection_type"),
                    get_report_table_header("target_count"),
                    get_report_table_header("percentage"),
                    get_report_table_header("defect_level")
                ]
                for i, header in enumerate(headers):
                    stats_table.cell(0, i).text = header

                for fault_type, count in fault_counts.items():
                    row_cells = stats_table.add_row().cells
                    percentage = get_report_statistic("percentage_format").format(value=count / total_detections * 100)

                    # 确定缺陷等级
                    defect_level = get_fault_category("level_1_fault")  # 默认值
                    for level, faults in fault_categories.items():
                        if any(fault_name in fault_type for fault_name in faults.keys()):
                            defect_level = level
                            break

                    row_cells[0].text = fault_type
                    row_cells[1].text = str(count)
                    row_cells[2].text = percentage
                    row_cells[3].text = defect_level

            doc.add_paragraph("")

            # 详细检测结果
            if self.saved_results:
                # 详细结果表
                doc.add_paragraph(get_report_statistic("detailed_detection_results"))
                detail_table = doc.add_table(rows=1, cols=6)
                detail_table.style = 'Table Grid'
                detail_headers = [
                    get_report_table_header("string_id"),
                    get_report_table_header("defect_type"),
                    get_report_table_header("detection_time"),
                    get_report_table_header("longitude"),
                    get_report_table_header("latitude"),
                    get_report_table_header("confidence")
                ]
                for i, header in enumerate(detail_headers):
                    detail_table.cell(0, i).text = header

                for idx, (detection_results, img_name) in enumerate(zip(self.saved_results, self.saved_names)):
                    # 尝试从图片路径获取GPS信息
                    gps_info = None
                    latitude_str = get_report_statistic("unknown_location")
                    longitude_str = get_report_statistic("unknown_location")

                    if enable_gps_parsing:
                        # 尝试从保存的图片路径中获取GPS信息
                        try:
                            img_path = None
                            if hasattr(self, 'saved_image_paths') and idx < len(self.saved_image_paths):
                                img_path = self.saved_image_paths[idx]

                            if img_path and os.path.exists(img_path):
                                gps_info = extract_gps_info(img_path)
                                if gps_info:
                                    if 'latitude' in gps_info:
                                        latitude_str = f"{gps_info['latitude']:.8f}"
                                    if 'longitude' in gps_info:
                                        longitude_str = f"{gps_info['longitude']:.8f}"
                        except Exception as e:
                            print(f"{get_system_message('gps_parse_failed').format(error=str(e))}")

                    for detInfo in detection_results:
                        if isinstance(detInfo, list) and len(detInfo) >= 6:
                            row_cells = detail_table.add_row().cells
                            row_cells[0].text = get_report_statistic("string_id_format").format(value=idx + 1)  # 组串编号
                            row_cells[1].text = str(detInfo[1])  # 缺陷类型
                            row_cells[2].text = report_time  # 检测时间
                            row_cells[3].text = longitude_str  # 经度
                            row_cells[4].text = latitude_str   # 纬度
                            row_cells[5].text = get_report_statistic("confidence_format").format(value=float(detInfo[3]) if isinstance(detInfo[3], (int, float, str)) else 0.95)  # 置信度

            # 添加图片检测结果
            doc.add_page_break()
            if model_type == get_system_default("model_type_segmentation"):
                doc.add_heading(get_report_field("segmentation_results_title"), level=1)
            else:
                doc.add_heading(get_report_field("detection_results_title"), level=1)

            # 遍历每张图片的检测结果
            for idx, (image_ini, image_detected, detection_results, img_name) in enumerate(
                zip(self.saved_images_ini, self.saved_images, self.saved_results, self.saved_names)
            ):
                # 添加图片标题
                doc.add_heading(get_report_field("image_title").format(idx=idx + 1, name=img_name), level=2)

                # 创建一个表格用于左右放置图片
                table = doc.add_table(rows=2, cols=2)
                table.autofit = True

                # 左侧放置原始图像
                cell_left = table.cell(0, 0)
                cell_left.text = get_report_field("original_image_label").format(label=image_type)
                original_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_ini, cv2.COLOR_BGR2RGB)).save(original_image_stream, format='PNG')
                original_image_stream.seek(0)
                table.cell(1, 0).paragraphs[0].add_run().add_picture(original_image_stream, width=Inches(3))

                # 右侧放置识别后的图像
                cell_right = table.cell(0, 1)
                if model_type == get_system_default("model_type_segmentation"):
                    cell_right.text = get_report_field("segmentation_result_label").format(label=image_type)
                else:
                    cell_right.text = get_report_field("detection_result_label").format(label=image_type)
                detected_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_detected, cv2.COLOR_BGR2RGB)).save(detected_image_stream, format='PNG')
                detected_image_stream.seek(0)
                table.cell(1, 1).paragraphs[0].add_run().add_picture(detected_image_stream, width=Inches(3))

                # 添加检测结果信息
                if detection_results:
                    if model_type == get_system_default("model_type_segmentation"):
                        doc.add_paragraph(get_report_field("segmented_targets").format(count=len(detection_results)))
                    else:
                        doc.add_paragraph(get_report_field("detected_targets").format(count=len(detection_results)))
                    for i, detInfo in enumerate(detection_results):
                        if isinstance(detInfo, list) and len(detInfo) >= 2:
                            doc.add_paragraph(f"  {i + 1}. {detInfo[1]} - {get_report_field('confidence_label')}: {detInfo[3] if len(detInfo) > 3 else 'N/A'}")
                else:
                    if model_type == get_system_default("model_type_segmentation"):
                        doc.add_paragraph(get_report_field("no_targets_detected"))
                    else:
                        doc.add_paragraph(get_report_field("no_anomalies_detected"))

                # 添加GPS信息（如果启用了GPS解析）
                if enable_gps_parsing:
                    try:
                        img_path = None
                        if hasattr(self, 'saved_image_paths') and idx < len(self.saved_image_paths):
                            img_path = self.saved_image_paths[idx]

                        if img_path and os.path.exists(img_path):
                            gps_info = extract_gps_info(img_path)
                            if gps_info:
                                doc.add_paragraph(get_report_field("gps_info_label"))
                                gps_text = format_gps_info(gps_info)
                                doc.add_paragraph(gps_text)
                            else:
                                doc.add_paragraph(get_report_field("gps_not_found"))
                        else:
                            doc.add_paragraph(get_report_field("gps_invalid_path"))
                    except Exception as e:
                        doc.add_paragraph(get_report_field("gps_parse_failed").format(error=str(e)))
                elif enable_gps_parsing:
                    doc.add_paragraph(get_report_field("gps_feature_unavailable"))

                doc.add_paragraph("")  # 添加间距

            # 保存 Word 文件
            doc.save(word_file_path)
            print(f"{get_system_message('save_to_word_success').format(path=word_file_path)}")

        except Exception as e:
            print(f"{get_system_message('save_to_word_failed').format(error=str(e))}")
            traceback.print_exc()

    def update_table(self, log_table_placeholder):
        """
        更新表格，显示最新的500条记录。

        Args:
            log_table_placeholder: Streamlit的表格占位符

        Returns:
            None
        """
        # 动态获取当前语言的列名
        current_columns = [
            get_table_column("file_path"),
            get_table_column("detection_result"),
            get_table_column("type"),
            get_table_column("location"),
            get_table_column("area"),
            get_table_column("time")
        ]

        # 判断DataFrame的长度是否超过500
        if len(self.data) > 500:
            # 如果超过500，仅显示最新的500条记录
            display_data = self.data.head(500).copy()
        else:
            # 如果不超过，显示全部数据
            display_data = self.data.copy()

        # 如果有数据，动态更新列名以支持语言切换
        if not display_data.empty:
            # 确保列数匹配
            if len(display_data.columns) == len(current_columns):
                display_data.columns = current_columns
            else:
                # 如果列数不匹配，重新创建DataFrame
                display_data = pd.DataFrame(display_data.values, columns=current_columns[:len(display_data.columns)])
        else:
            # 如果没有数据，创建一个带有正确列名的空DataFrame
            display_data = pd.DataFrame(columns=current_columns)

        log_table_placeholder.table(display_data)
