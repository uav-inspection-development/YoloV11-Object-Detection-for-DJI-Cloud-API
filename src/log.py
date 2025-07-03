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

        self.columns = ['文件路径', '识别结果', '类型', '位置(pixel)', '面积(pixel)', '时间(s)']
        self.data = pd.DataFrame(columns=self.columns)

    def add_frames(self, image, detInfo, img_ini, img_name=None):
        """
        将检测到的图像和检测信息添加到列表中。

        Args:
            image (numpy.ndarray): 检测到的图像。
            detInfo (list): 检测信息。
            img_ini (numpy.ndarray): 初始图像。
            img_name (str): 图像名称。
        """
        self.saved_images.append(image)
        self.saved_images_ini.append(img_ini)
        self.saved_results.append(detInfo)
        self.saved_names.append(img_name)
        
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

    def save_to_word(self, word_file_path):
        """
        将检测结果保存到 Word 文件。

        Args:
            word_file_path (str): Word 文件的路径。
        """
        try:
            # 创建一个 Word 文档
            doc = Document()
            doc.add_heading('检测结果报告', level=1).alignment = 1  # 标题居中

            # 添加首页信息并居中
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            total_images = len(self.saved_images)
            doc.add_paragraph().add_run("\n").bold = True  # 添加空行
            doc.add_paragraph(f"报告生成日期：{now}").paragraph_format.alignment = 1  # 居中
            doc.add_paragraph(f"包含图片数量：{total_images}").paragraph_format.alignment = 1  # 居中
            doc.add_paragraph("\n").paragraph_format.alignment = 1  # 添加空行

            # 插入分页符
            doc.add_page_break()

            # 遍历每张图片的检测结果
            for idx, (image_ini, image_detected, detection_results, img_name) in enumerate(
                zip(self.saved_images_ini, self.saved_images, self.saved_results, self.saved_names)
            ):
                # 添加图片标题，使用标题字体并居中
                title = doc.add_heading(f'图片 {idx + 1}: {img_name}', level=2)
                title.alignment = 1  # 居中

                # 创建一个表格用于左右放置图片
                table = doc.add_table(rows=1, cols=2)
                table.autofit = True

                # 左侧放置原始图像
                cell_left = table.cell(0, 0)
                cell_left.paragraphs[0].add_run('原始图像:').bold = True
                original_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_ini, cv2.COLOR_BGR2RGB)).save(original_image_stream, format='PNG')
                original_image_stream.seek(0)
                cell_left.add_paragraph().add_run().add_picture(original_image_stream, width=Inches(3))

                # 右侧放置识别后的图像
                cell_right = table.cell(0, 1)
                cell_right.paragraphs[0].add_run('识别后的图像:').bold = True
                detected_image_stream = BytesIO()
                Image.fromarray(cv2.cvtColor(image_detected, cv2.COLOR_BGR2RGB)).save(detected_image_stream, format='PNG')
                detected_image_stream.seek(0)
                cell_right.add_paragraph().add_run().add_picture(detected_image_stream, width=Inches(3))

                # 添加检测结果表格
                doc.add_paragraph('检测结果信息:').paragraph_format.alignment = 1  # 居中
                table = doc.add_table(rows=1, cols=6)
                table.style = 'Table Grid'
                headers = ["识别结果", "类型", "位置(pixel)", "面积(pixel)", "时间(s)", "类别ID"]
                for i, header in enumerate(headers):
                    table.cell(0, i).text = header

                # 填充检测结果
                for detInfo in detection_results:
                    if isinstance(detInfo, list) and len(detInfo) == 6:
                        row_cells = table.add_row().cells
                        for i, value in enumerate(detInfo):
                            row_cells[i].text = str(value)

                # 添加段落间距
                doc.add_paragraph("\n")

            # 保存 Word 文件
            doc.save(word_file_path)
            print(f"检测结果已保存到 Word 文件: {word_file_path}")

        except Exception as e:
            print(f"保存到 Word 文件失败: {str(e)}")

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