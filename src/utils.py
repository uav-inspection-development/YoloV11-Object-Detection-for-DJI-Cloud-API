import os

import cv2
import numpy as np
import pandas as pd
from PIL import ImageFont, ImageDraw, Image
from hashlib import md5
from QtFusion.path import abs_path
from matplotlib.colors import LinearSegmentedColormap
from pathlib import Path
from scipy.optimize import minimize

def save_uploaded_file(uploaded_file):
    """
    保存上传的文件到服务器上。

    Args:
        uploaded_file (UploadedFile): 通过Streamlit上传的文件。

    Returns:
        str: 保存文件的完整路径，如果没有文件上传则返回 None。

    当用户上传文件时，将该文件保存到服务器的指定目录中。
    """
    # 检查是否有文件上传
    if uploaded_file is not None:
        base_path = "tempDir"  # 定义文件保存的基本路径

        # 如果路径不存在，创建这个路径
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        # 获取文件的完整路径
        file_path = os.path.join(base_path, uploaded_file.name)

        # 以二进制写模式打开文件
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())  # 写入文件

        return file_path  # 返回文件路径

    return None  # 如果没有文件上传，返回 None


def concat_results(result, location, confidence, time):
    """
    显示检测结果。

    Args:
        result (str): 检测结果。
        location (str): 检测位置。
        confidence (str): 置信度。
        time (str): 检测用时。
    """
    # 创建一个包含这些信息的 DataFrame
    result_data = {
        "识别结果": [result],
        "位置": [location],
        "置信度": [confidence],
        "用时": [time]
    }

    results_df = pd.DataFrame(result_data)
    return results_df


def load_default_image():
    """
    加载默认图片。

    Returns:
        Image: 返回默认图片对象。
    """
    ini_image = abs_path("../icon/ini-image.png")
    return Image.open(ini_image)


def get_camera_names():
    """
    获取可用摄像头名称列表。

    Returns:
        list: 返回包含“未启用摄像头”和可用摄像头索引号的列表。
    """
    camera_names = ["摄像头检测关闭", "0"]
    max_test_cameras = 10  # 定义要测试的最大摄像头数量，可以根据需要调整

    for i in range(max_test_cameras):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened() and str(i) not in camera_names:
            camera_names.append(str(i))
            cap.release()
    return camera_names


def calculate_polygon_area(points):
    """
    计算多边形面积的函数

    Args:
        points (numpy.ndarray): 多边形的顶点坐标，形状为 (N, 2)，其中 N 是顶点数量
    """
    return cv2.contourArea(points.astype(np.float32))


# def draw_with_chinese(img, text, position, font_size):
#     """
#     假设这是一个自定义函数，用于在图像上绘制中文文本
#     具体实现需要根据你的需求进行调整

#     Args:
#         img (numpy.ndarray): 输入图像
#         text (str): 要绘制的文本
#         position (tuple): 文本位置 (x, y)
#         font_size (int): 字体大小
#     """
#     font = cv2.FONT_HERSHEY_SIMPLEX
#     color = (255, 255, 255)
#     thickness = 2
#     cv2.putText(img, text, position, font, font_size, color, thickness, cv2.LINE_AA)
#     return img


def generate_color_based_on_name(name):
    """
    使用哈希函数生成稳定的颜色

    Args:
        name (str): 类别名称
    """
    hash_object = md5(name.encode())
    hex_color = hash_object.hexdigest()[:6]  # 取前6位16进制数
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return (b, g, r)  # OpenCV 使用BGR格式


def draw_with_chinese(image, text, position, font_size=20, color=(255, 0, 0)):
    """
    在OpenCV图像上绘制中文文字

    Args:
        image (numpy.ndarray): 输入图像
        text (str): 要绘制的文本
        position (tuple): 文本位置 (x, y)
        font_size (int): 字体大小
        color (tuple): 颜色 (B, G, R)
    """
    # 将图像从 OpenCV 格式（BGR）转换为 PIL 格式（RGB）
    image_pil = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(image_pil)
    # 使用指定的字体
    font = ImageFont.truetype("simsun.ttc", font_size, encoding="unic")
    draw.text(position, text, font=font, fill=color)
    # 将图像从 PIL 格式（RGB）转换回 OpenCV 格式（BGR）
    return cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)


def adjust_parameter(image_size, base_size=1000):
    """
    计算自适应参数，基于图片的最大尺寸

    Args:
        image_size (tuple): 图像的尺寸 (height, width)
        base_size (int): 基准尺寸，默认为 1000
    """
    max_size = max(image_size)
    return max_size / base_size


def draw_detections(image, info, color = (0, 0, 255), alpha=0.2, line_number=None):
    """
    在图像上绘制检测结果，包括边界框、类别名称和掩码（如果有）

    Args:
        image (numpy.ndarray): 输入图像
        info (dict): 检测信息，包括类别名称、边界框、置信度、类别ID和掩码
        color (tuple): 边界框颜色，默认为红色 (0, 0, 255)
        alpha (float): 透明度参数，默认为 0.2
        line_number (int): 行号，用于在检测框中间绘制行号，默认为 None
    """
    name, bbox, conf, cls_id, mask = info['class_name'], info['bbox'], info['score'], info['class_id'], info['mask']
    adjust_param = adjust_parameter(image.shape[:2])
    spacing = int(20 * adjust_param)

    if mask is None:
        x1, y1, x2, y2 = bbox
        aim_frame_area = (x2 - x1) * (y2 - y1)
        cv2.rectangle(image, (x1, y1), (x2, y2), color=color, thickness=int(5 * adjust_param))
        image = draw_with_chinese(image, name, (x1, y1 - int(30 * adjust_param)), font_size=int(35 * adjust_param), color=color)
        y_offset = int(50 * adjust_param)  # 类别名称上方绘制，其下方留出空间
    else:
        mask_points = np.concatenate(mask)
        aim_frame_area = calculate_polygon_area(mask_points)
        mask_color = generate_color_based_on_name(name)
        try:
            overlay = image.copy()
            cv2.fillPoly(overlay, [mask_points.astype(np.int32)], mask_color)
            image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
            cv2.drawContours(image, [mask_points.astype(np.int32)], -1, color=color, thickness=int(8 * adjust_param))

            # 计算面积、周长、圆度
            area = cv2.contourArea(mask_points.astype(np.int32))
            perimeter = cv2.arcLength(mask_points.astype(np.int32), True)
            circularity = 4 * np.pi * area / (perimeter ** 2) if perimeter > 0 else 0

            # 计算色彩
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [mask_points.astype(np.int32)], -1, 255, -1)
            color_points = cv2.findNonZero(mask)
            selected_points = color_points[np.random.choice(color_points.shape[0], 5, replace=False)]
            colors = np.mean([image[y, x] for x, y in selected_points[:, 0]], axis=0)
            color_str = f"({colors[0]:.1f}, {colors[1]:.1f}, {colors[2]:.1f})"

            # 绘制类别名称
            x, y = np.min(mask_points, axis=0).astype(int)
            image = draw_with_chinese(image, name, (x, y - int(30 * adjust_param)), font_size=int(35 * adjust_param), color=color)
            y_offset = int(50 * adjust_param)  # 类别名称上方绘制，其下方留出空间

            # 绘制面积、周长、圆度和色彩值
            # metrics = [("Area", area), ("Perimeter", perimeter), ("Circularity", circularity), ("Color", color_str)]
            # for idx, (metric_name, metric_value) in enumerate(metrics):
            #     text = f"{metric_name}: {metric_value}"
            #     image = draw_with_chinese(image, text, (x, y - y_offset - spacing * (idx + 1)),
            #                               font_size=int(35 * adjust_param), color=color)

        except Exception as e:
            print(f"An error occurred: {e}")

    # 在检测框中间绘制行号
    if line_number is not None:
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        image = draw_with_chinese(image, str(line_number), (center_x, center_y), font_size=int(20 * adjust_param), color=color)

    return image, aim_frame_area


def calculate_polygon_area(points):
    """
    计算多边形的面积

    Args:
        points (numpy.ndarray): 多边形的顶点坐标，形状为 (N, 2)，其中 N 是顶点数量
    """
    if len(points) < 3:  # 多边形至少需要3个顶点
        return 0
    return cv2.contourArea(points)


def format_time(seconds):
    """
    将秒数转换为时:分:秒格式的字符串

    Args:
        seconds (int): 秒数
    """
    # 计算小时、分钟和秒
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    # 格式化为字符串
    return "{:02}:{:02}:{:02}".format(int(hrs), int(mins), int(secs))


def save_chinese_image(file_path, image_array):
    """
    保存带有中文路径的图片文件

    参数：
    file_path (str): 图片的保存路径，应包含中文字符, 例如 '示例路径/含有中文的文件名.png'
    image_array (numpy.ndarray): 要保存的 OpenCV 图像（即 numpy 数组）
    """
    dir_path = os.path.dirname(file_path)
    dir_path = Path(dir_path)
    # 检查目录是否存在
    if not dir_path.exists():
        # 如果目录不存在，则创建它
        dir_path.mkdir(parents=True, exist_ok=True)

    try:
        # 将 OpenCV 图片转换为 Pillow Image 对象
        image = Image.fromarray(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))

        # 使用 Pillow 保存图片文件
        image.save(file_path)

        print(f"成功保存图像到: {file_path}")
    except Exception as e:
        print(f"保存图像失败: {str(e)}")


def convert_to_pseudo_colorizer(image, contrast=1.0, brightness=0):
    """
    将灰度图像转换为伪彩色图像，使用自定义的颜色映射。

    参数:
        image (PIL.Image.Image): 输入的灰度图像。
        contrast (float): 对比度调整因子（默认值为1.0）。
        brightness (int): 亮度调整值（范围为-255到255，默认值为0）。

    返回:
        PIL.Image.Image: 伪彩色图像，如果输入不是灰度图像则返回 None。
    """
    # 定义自定义颜色映射的颜色
    colors = [
        (0.0, (128, 128, 128)),  # 最低温度：黑色
        (0.3, (128, 0, 128)),  # 低温温度：紫色
        (0.8, (255, 50, 0)),  # 高温区域：红色
        (1.0, (255, 255, 0))  # 最高温度：黄色
    ]

    # 创建自定义颜色映射
    colors = sorted([(pos, tuple(np.array(color) / 255)) for pos, color in colors], key=lambda x: x[0])
    colormap = LinearSegmentedColormap.from_list("custom", [(pos, color) for pos, color in colors])

    # 将图像转换为 NumPy 数组
    img_array = np.array(image)

    # 应用对比度和亮度调整
    img_array = np.clip(img_array.astype(np.float32) * contrast + brightness, 0, 255).astype(np.uint8)

    # 应用颜色映射
    colored_array = colormap(img_array / 255.0)[:, :, :3]  # 忽略alpha通道
    colored_array = (colored_array * 255).astype(np.uint8)

    # 将彩色数组转换回 PIL 图像
    pseudo_colored_img = Image.fromarray(colored_array)

    return pseudo_colored_img


def is_black_and_white(image_array):
    """
    判断一个 RGB 图像是否是黑白图像。

    参数:
        image_array (numpy.ndarray): 输入的 RGB 图像数组。

    返回:
        bool: 如果图像是黑白图像，返回 True；否则返回 False。
    """
    # 检查图像是否为 RGB 格式
    if len(image_array.shape) != 3 or image_array.shape[2] != 3:
        return

    # 检查每个像素的 R、G、B 通道值是否相等
    is_bw = np.all(image_array[:, :, 0] == image_array[:, :, 1]) and np.all(image_array[:, :, 1] == image_array[:, :, 2])

    return is_bw

def camera_undistortion(frame, camera_matrix=None, dist_coeffs=None):
    """
    对输入帧进行去畸变处理。

    参数：
        frame (numpy.ndarray): 输入的图像帧。
        camera_matrix (numpy.ndarray): 相机内参矩阵。
        dist_coeffs (numpy.ndarray): 相机畸变系数。

    返回：
        numpy.ndarray: 去畸变后的图像帧。
    """
    if camera_matrix is not None and dist_coeffs is not None:
        try:
            h, w = frame.shape[:2]
            new_camera_mtx, roi = cv2.getOptimalNewCameraMatrix(
                camera_matrix, dist_coeffs, (w, h), 1, (w, h)
            )
            undistorted = cv2.undistort(frame, camera_matrix, dist_coeffs, None, new_camera_mtx)
            # 可选：裁剪ROI
            x, y, w, h = roi
            undistorted = undistorted[y:y+h, x:x+w]
            return undistorted
        except Exception as e:
            print(f"去畸变失败: {e}")
            return frame
    return frame

def auto_undistort_image(img):
    """
    自动根据图像中的线条进行去畸变处理。

    参数：
        img (numpy.ndarray): 输入的图像。

    返回：
        numpy.ndarray: 去畸变后的图像。
    """
    def extract_lines(gray_img):
        # Step 1: Edge detection
        edges = cv2.Canny(gray_img, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=50, maxLineGap=20)
        if lines is None:
            return []
        return [((x1, y1), (x2, y2)) for [[x1, y1, x2, y2]] in lines]

    def interpolate_line_points(lines):
        """Generate multiple points between endpoints of lines."""
        all_points = []
        for (x1, y1), (x2, y2) in lines:
            line_pts = np.linspace((x1, y1), (x2, y2), 20)  # 20 interpolated points per line
            all_points.append(line_pts)
        return all_points

    def distort_points(points, k1, cx, cy):
        result = []
        for x, y in points:
            dx, dy = x - cx, y - cy
            r2 = dx * dx + dy * dy
            factor = 1 + k1 * r2
            result.append((cx + dx * factor, cy + dy * factor))
        return np.array(result)

    def straightness_loss(k1, lines_pts, cx, cy):
        loss = 0
        for pts in lines_pts:
            pts = distort_points(pts, k1, cx, cy)
            [vx, vy, x0, y0] = cv2.fitLine(pts.astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01)
            # Orthogonal distance of all points to the line
            for x, y in pts:
                dist = abs(vy * x - vx * y + (x0 * vy - y0 * vx)) / np.sqrt(vx**2 + vy**2)
                loss += dist**2
        return loss

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lines = extract_lines(gray)
    if len(lines) < 5:
        print("Not enough lines found for correction.")
        return img.copy()

    # Prepare data
    h, w = gray.shape
    cx, cy = w / 2, h / 2
    interpolated_lines = interpolate_line_points(lines)

    # Optimize distortion coefficient (start at 0, typical k1 range is [-0.5, 0.5])
    result = minimize(lambda k: straightness_loss(k[0], interpolated_lines, cx, cy), [0.0],
                      bounds=[(-0.5, 0.5)], method='L-BFGS-B')

    k1 = result.x[0]
    print(f"Estimated distortion k1 = {k1:.5f}")

    # Undistort image using OpenCV remap
    K = np.array([[w, 0, cx], [0, w, cy], [0, 0, 1]])  # approximate fx = fy = w
    D = np.array([k1, 0, 0, 0])  # only k1 used

    map1, map2 = cv2.initUndistortRectifyMap(K, D, None, K, (w, h), cv2.CV_32FC1)
    undistorted = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)

    return undistorted