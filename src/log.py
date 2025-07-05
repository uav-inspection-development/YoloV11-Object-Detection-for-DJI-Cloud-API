import os
import time
import cv2
import pandas as pd
from QtFusion.path import abs_path
from PIL import Image
import numpy as np
from datetime import datetime
from docx import Document
from docx.shared import Inches
from io import BytesIO

try:
    from utils import extract_gps_info, format_gps_info
    GPS_PARSING_AVAILABLE = True
except ImportError:
    GPS_PARSING_AVAILABLE = False
    def extract_gps_info(image_path):
        return None
    def format_gps_info(gps_info):
        return "GPS解析功能不可用"

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

        print(f"成功保存图像到: {file_path}")
    except Exception as e:
        print(f"保存图像失败: {str(e)}")

class ResultLogger:
    def __init__(self):
        """
        初始化ResultLogger类。
        """
        self.results_df = pd.DataFrame(columns=["识别结果", "类型","位置(pixel)", "面积(pixel)", "时间(s)"])

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
            "识别结果": [result],
            "类型": [chinese_name],
            "位置(pixel)": [location],
            "面积(pixel)": [confidence],
            "时间(s)": [time]
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

        self.columns = ['文件路径', '识别结果', '类型', '位置(pixel)', '面积(pixel)', '时间(s)']
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
        current_targets = ["全部目标"]  # 默认包含"全部目标"选项
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
            
            model_type = detection_params.get('model_type', '检测任务')
            image_type = detection_params.get('image_type', '其他')
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
            title_run = title_para.add_run("无人机光伏巡检报告")
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
            report_num_para = doc.add_paragraph(f"报告编号：{report_num}")
            report_num_para.alignment = 1  # 居中

            # 第一页结束，插入分页符进入目录页
            doc.add_page_break()

            # 第二页：目录页
            toc_title = doc.add_heading("目录", level=1)
            toc_title.alignment = 1  # 居中
            
            # 添加空行
            doc.add_paragraph("")
            
            # 目录内容，使用表格格式实现点线对齐
            toc_table = doc.add_table(rows=5, cols=2)
            toc_table.style = 'Light List'
            
            # 目录项
            toc_items = [
                ("1、概述", "3"),
                ("2、光伏电站故障维修建议", "4"), 
                ("3、结果统计", "5"),
                ("4、详细检测结果", "6"),
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
            doc.add_heading("1、概述", level=1)
            overview_table = doc.add_table(rows=8, cols=2)
            overview_table.style = 'Table Grid'
            
            # 根据检测类型和图像类型生成检测场景描述
            scene_desc = f"{image_type}{model_type}"
            if model_type == "分割任务":
                scene_desc += f" - 对{image_type}图像进行光伏板轮廓分割"
            else:
                scene_desc += f" - 对{image_type}图像进行异常检测"
            
            # 概述表格数据
            overview_data = [
                ["使用单位", "光伏电站"],
                ["检测场景", scene_desc],
                ["检测类型", f"{model_type} - {image_type}"],
                ["飞行批号", f"UAV-{now.strftime('%Y%m%d')}"],
                ["任务名称", f"光伏巡检任务-{now.strftime('%Y%m%d')}"],
                ["报告日期", report_time],
                ["检测图片数量", str(len(self.saved_images))],
                ["检测参数", f"置信度: {conf_threshold}, IOU: {iou_threshold}"]
            ]
            
            for i, (key, value) in enumerate(overview_data):
                overview_table.cell(i, 0).text = key
                overview_table.cell(i, 1).text = value

            doc.add_paragraph("")
            
            # 概述部分结束，插入分页符进入故障建议部分
            doc.add_page_break()
            
            # 2、光伏电站故障维修建议
            doc.add_heading("2、光伏电站故障维修建议", level=1)
            
            # 根据检测类型定义不同的故障分类
            if image_type == "EL隐裂":
                fault_categories = {
                    "一级故障": {
                        "划伤": "组件表面出现划伤，建议检查并及时维护，避免进一步损坏。",
                        "黑片": "检测到黑片异常，建议追踪观察并考虑维修。"
                    },
                    "二级故障": {
                        "隐裂": "组件内部出现隐裂，建议立即检修或更换，避免电性能下降。",
                        "碎片": "组件表面或内部出现碎片，建议立即更换组件。",
                        "缺角": "组件出现缺角损坏，建议评估影响程度并考虑更换。"
                    }
                }
            elif image_type == "红外":
                fault_categories = {
                    "一级故障": {
                        "阳光反射": "红外图像中的阳光反射，属于正常现象，无需处理。",
                        "光伏板正常热成像": "组件热成像正常，无异常发热。"
                    },
                    "二级故障": {
                        "单一热斑": "单个组件出现热斑，建议检查组件连接和清洁度。",
                        "异常低温": "组件温度异常偏低，建议检查电路连接。"
                    },
                    "三级故障": {
                        "大面积热斑": "大面积热斑异常，建议立即检查电路和组件状态。",
                        "二极管短路": "旁路二极管故障，建议立即维修或更换。"
                    }
                }
            elif image_type == "可见光":
                fault_categories = {
                    "一级故障": {
                        "脏污": "组件表面脏污，建议清洁以保证发电效率。",
                        "鸟粪": "组件表面有鸟粪，建议清理并考虑防鸟措施。",
                        "积雪": "组件表面积雪，建议及时清理。"
                    },
                    "二级故障": {
                        "遮挡": "组件被遮挡，建议清除遮挡物或调整组件角度。",
                        "隐裂": "可见光下发现隐裂，建议进一步检查。"
                    },
                    "三级故障": {
                        "面板碎裂": "组件表面玻璃破损，建议立即更换。",
                        "光伏板缺失": "组件缺失，建议立即补装。",
                        "光伏板组件变形": "组件变形，建议检查支架和更换组件。"
                    }
                }
            else:
                # 默认故障分类（其他类型或分割任务）
                fault_categories = {
                    "检测信息": {
                        "单组件": "成功分割识别单个光伏组件。",
                        "组串": "成功分割识别光伏组串。",
                        "行人": "检测到人员活动，建议注意安全。",
                        "车辆": "检测到车辆，建议注意交通管制。"
                    }
                } if model_type == "分割任务" or image_type == "其他" else {
                    "一级故障": {
                        "异物遮挡": "组件表面草本、固定物等阴影遮挡，产生局部温度，建议进行面板遮挡消除。",
                        "脏污": "组件表面可能因灰尘颗粒物等导致热斑，建议进行面板清理，避免光伏面板受损",
                        "热斑": "光伏件呈现热斑效应。"
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
            doc.add_heading("3、结果统计", level=1)
            
            # 统计信息
            total_detections = sum(len(results) for results in self.saved_results)
            fault_counts = {}
            for detection_results in self.saved_results:
                for detInfo in detection_results:
                    if isinstance(detInfo, list) and len(detInfo) >= 2:
                        fault_type = detInfo[1]
                        fault_counts[fault_type] = fault_counts.get(fault_type, 0) + 1
            
            # 算法引擎描述
            if model_type == "分割任务":
                doc.add_paragraph("无人机飞行后对本次航线进行了全方位的智能分割分析后得出此报告。")
                algorithm_desc = f"采用YOLOv11分割算法对{image_type}图像进行光伏组件轮廓分割"
            else:
                doc.add_paragraph("无人机飞行后对本次航线进行了全方位的算法检测分析后得出此报告。")
                algorithm_desc = f"采用YOLOv11检测算法对{image_type}图像进行异常检测"
            
            engines = list(fault_counts.keys()) if fault_counts else ["未检测到异常"]
            doc.add_paragraph(f"使用的算法引擎：{algorithm_desc}")
            doc.add_paragraph(f"检测到的类别：（{', '.join(engines)}）")
            doc.add_paragraph("")
            
            # 报警次数统计
            if total_detections > 0:
                doc.add_paragraph(f"报警次数为：{total_detections} 次，其中：")
                for fault_type, count in fault_counts.items():
                    doc.add_paragraph(f"{fault_type}：{count}次；")
            else:
                doc.add_paragraph("报警次数为：0 次")
            
            doc.add_paragraph("")
            
            # 检测类型总统计表
            if fault_counts:
                doc.add_paragraph("检测类型总统计：")
                stats_table = doc.add_table(rows=1, cols=4)
                stats_table.style = 'Table Grid'
                headers = ["检测类型", "目标数量", "占总检测数量", "缺陷等级"]
                for i, header in enumerate(headers):
                    stats_table.cell(0, i).text = header
                
                for fault_type, count in fault_counts.items():
                    row_cells = stats_table.add_row().cells
                    percentage = f"{(count / total_detections * 100):.1f}%"
                    
                    # 确定缺陷等级
                    defect_level = "一级故障"  # 默认值
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
                doc.add_paragraph("详细检测结果：")
                detail_table = doc.add_table(rows=1, cols=6)
                detail_table.style = 'Table Grid'
                detail_headers = ["组串", "缺陷类型", "检测时间", "经度", "纬度", "置信度"]
                for i, header in enumerate(detail_headers):
                    detail_table.cell(0, i).text = header
                
                for idx, (detection_results, img_name) in enumerate(zip(self.saved_results, self.saved_names)):
                    # 尝试从图片路径获取GPS信息
                    gps_info = None
                    latitude_str = "未知"
                    longitude_str = "未知"
                    
                    if enable_gps_parsing and GPS_PARSING_AVAILABLE:
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
                            print(f"解析GPS信息时出错: {e}")
                    
                    for detInfo in detection_results:
                        if isinstance(detInfo, list) and len(detInfo) >= 6:
                            row_cells = detail_table.add_row().cells
                            row_cells[0].text = f"{idx + 1:06d}"  # 组串编号
                            row_cells[1].text = str(detInfo[1])  # 缺陷类型
                            row_cells[2].text = report_time  # 检测时间
                            row_cells[3].text = longitude_str  # 经度
                            row_cells[4].text = latitude_str   # 纬度
                            row_cells[5].text = f"{float(detInfo[3]) if isinstance(detInfo[3], (int, float, str)) else 0.95:.2f}"  # 置信度

            # 添加图片检测结果
            doc.add_page_break()
            if model_type == "分割任务":
                doc.add_heading("分割图片详细结果", level=1)
            else:
                doc.add_heading("检测图片详细结果", level=1)
            
            # 遍历每张图片的检测结果
            for idx, (image_ini, image_detected, detection_results, img_name) in enumerate(
                zip(self.saved_images_ini, self.saved_images, self.saved_results, self.saved_names)
            ):
                # 添加图片标题
                doc.add_heading(f'图片 {idx + 1}: {img_name}', level=2)

                # 创建一个表格用于左右放置图片
                table = doc.add_table(rows=2, cols=2)
                table.autofit = True

                # 左侧放置原始图像
                cell_left = table.cell(0, 0)
                cell_left.text = f'原始{image_type}图片'
                original_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_ini, cv2.COLOR_BGR2RGB)).save(original_image_stream, format='PNG')
                original_image_stream.seek(0)
                table.cell(1, 0).paragraphs[0].add_run().add_picture(original_image_stream, width=Inches(3))

                # 右侧放置识别后的图像
                cell_right = table.cell(0, 1)
                if model_type == "分割任务":
                    cell_right.text = f'{image_type}分割结果'
                else:
                    cell_right.text = f'{image_type}检测结果'
                detected_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_detected, cv2.COLOR_BGR2RGB)).save(detected_image_stream, format='PNG')
                detected_image_stream.seek(0)
                table.cell(1, 1).paragraphs[0].add_run().add_picture(detected_image_stream, width=Inches(3))

                # 添加检测结果信息
                if detection_results:
                    if model_type == "分割任务":
                        doc.add_paragraph(f'分割到 {len(detection_results)} 个目标：')
                    else:
                        doc.add_paragraph(f'检测到 {len(detection_results)} 个目标：')
                    for i, detInfo in enumerate(detection_results):
                        if isinstance(detInfo, list) and len(detInfo) >= 2:
                            doc.add_paragraph(f"  {i+1}. {detInfo[1]} - 置信度: {detInfo[3] if len(detInfo) > 3 else 'N/A'}")
                else:
                    if model_type == "分割任务":
                        doc.add_paragraph('未检测到目标')
                    else:
                        doc.add_paragraph('未检测到异常')
                
                # 添加GPS信息（如果启用了GPS解析）
                if enable_gps_parsing and GPS_PARSING_AVAILABLE:
                    try:
                        img_path = None
                        if hasattr(self, 'saved_image_paths') and idx < len(self.saved_image_paths):
                            img_path = self.saved_image_paths[idx]
                        
                        if img_path and os.path.exists(img_path):
                            gps_info = extract_gps_info(img_path)
                            if gps_info:
                                doc.add_paragraph("GPS信息:")
                                gps_text = format_gps_info(gps_info)
                                doc.add_paragraph(gps_text)
                            else:
                                doc.add_paragraph("GPS信息: 未找到GPS信息")
                        else:
                            doc.add_paragraph("GPS信息: 图片路径无效或文件不存在")
                    except Exception as e:
                        doc.add_paragraph(f"GPS信息: 解析失败 - {str(e)}")
                elif enable_gps_parsing:
                    doc.add_paragraph("GPS信息: GPS解析功能不可用")
                
                doc.add_paragraph("")  # 添加间距

            # 保存 Word 文件
            doc.save(word_file_path)
            print(f"光伏巡检报告已保存到: {word_file_path}")

        except Exception as e:
            print(f"保存到 Word 文件失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def update_table(self, log_table_placeholder):
        """
        更新表格，显示最新的500条记录。

        Args:
            log_table_placeholder: Streamlit的表格占位符

        Returns:
            None
        """
        # 判断DataFrame的长度是否超过500
        if len(self.data) > 500:
            # 如果超过500，仅显示最新的500条记录
            display_data = self.data.head(500)
        else:
            # 如果不超过，显示全部数据
            display_data = self.data

        log_table_placeholder.table(display_data)