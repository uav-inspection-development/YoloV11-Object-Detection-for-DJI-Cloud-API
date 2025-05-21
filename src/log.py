import os
import time
import cv2
import pandas as pd
from QtFusion.path import abs_path
from PIL import Image
import numpy as np
from datetime import datetime

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
        self.results_df = pd.DataFrame(columns=["识别结果", "类型","位置", "面积(pixel)", "时间(s)"])

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
            "位置": [location],
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

        columns = ['文件路径', '识别结果', '类型', '位置', '面积(pixel)', '时间(s)']

        # 尝试从CSV文件加载数据，如果失败则创建一个空的DataFrame
        try:
            # 检查CSV文件是否存在
            if not os.path.exists(csv_file_path):
                # 如果文件不存在，创建一个带有初始表头的空DataFrame并保存为CSV文件
                empty_df = pd.DataFrame(columns=columns)
                empty_df.to_csv(csv_file_path, index=False, header=True)

            self.data = pd.DataFrame(columns=columns)
            # self.data = pd.read_csv(csv_file_path, encoding='utf-8')
        except (FileNotFoundError, pd.errors.EmptyDataError):
            columns = ['文件路径', '识别结果', '类型', '位置', '面积(pixel)', '时间(s)']
            self.data = pd.DataFrame(columns=columns)

    def add_frames(self, image, detInfo, img_ini):
        """
        将检测到的图像和检测信息添加到列表中。

        Args:
            image (numpy.ndarray): 检测到的图像。
            detInfo (list): 检测信息。
            img_ini (numpy.ndarray): 初始图像。
        """
        self.saved_images.append(image)
        self.saved_images_ini.append(img_ini)
        self.saved_results = detInfo
        if detInfo:
            self.saved_target_images.append(image)
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

    def save_frames_file(self, fps=30, video_name='save', video_time=None, output_path='tempDir/frame/'):
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
                                 columns=['文件路径', '识别结果', '类型', '位置', '面积(pixel)', '时间(s)'])

        # 将新行添加到DataFrame中
        self.data = pd.concat([self.data, new_entry]).reset_index(drop=True)

        return self.data

    def clear_data(self):
        """
        清空数据表格。
        """
        columns = ['文件路径', '识别结果', '类型', '位置', '面积(pixel)', '时间(s)']
        self.data = pd.DataFrame(columns=columns)

    def save_to_csv(self, csv_file_path):
        """
        将数据保存到CSV文件。

        Args:
            csv_file_path (str): CSV文件的路径。
        """
        # 将更新后的DataFrame保存到CSV文件
        self.data.to_csv(csv_file_path, index=False, encoding='utf-8', mode='a', header=False)

    def save_to_excel(self, excel_file_path):
        """
        将数据保存到Excel文件。

        Args:
            excel_file_path (str): Excel文件的路径。
        """
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