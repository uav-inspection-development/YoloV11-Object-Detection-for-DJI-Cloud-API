import io
import os
from hashlib import md5
from pathlib import Path

import cv2
import exifread
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw, ImageFont
from PIL.ExifTags import GPSTAGS, TAGS
from QtFusion.path import abs_path
from scipy.optimize import minimize


class LocalFileObj(io.BytesIO):
    def __init__(self, file_path):
        with open(file_path, "rb") as f:
            super().__init__(f.read())
        self.name = os.path.basename(file_path)


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
        "用时": [time],
    }

    results_df = pd.DataFrame(result_data)
    return results_df


def load_default_image():
    """
    加载默认图片。

    Returns:
        Image: 返回默认图片对象。
    """
    ini_image = abs_path("../icon/ini.jpg")
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


def draw_detections(
    image,
    info,
    color=(0, 0, 255),
    alpha=0.2,
    line_number=None,
    is_api=False,
    rectangle_bbox=False,
):
    """
    在图像上绘制检测结果，包括边界框、类别名称和掩码（如果有）

    Args:
        image (numpy.ndarray): 输入图像
        info (dict): 检测信息，包括类别名称、边界框、置信度、类别ID和掩码
        color (tuple): 边界框颜色，默认为红色 (0, 0, 255)
        alpha (float): 透明度参数，默认为 0.2
        line_number (int): 行号，用于在检测框中间绘制行号，默认为 None
        rectangle_bbox (bool): 是否绘制掩码的最小外接矩形，默认为 False
    """
    name, bbox, conf, cls_id, mask = (
        info["class_name"],
        info["bbox"],
        info["score"],
        info["class_id"],
        info["mask"],
    )
    adjust_param = adjust_parameter(image.shape[:2])
    spacing = int(20 * adjust_param)

    if mask is None:
        x1, y1, x2, y2 = bbox
        aim_frame_area = (x2 - x1) * (y2 - y1)
        cv2.rectangle(
            image, (x1, y1), (x2, y2), color=color, thickness=int(5 * adjust_param)
        )
        image = draw_with_chinese(
            image,
            name,
            (x1, y1 - int(30 * adjust_param)),
            font_size=int(35 * adjust_param),
            color=color,
        )
        y_offset = int(50 * adjust_param)  # 类别名称上方绘制，其下方留出空间
    else:
        mask_points = np.concatenate(mask)
        aim_frame_area = calculate_polygon_area(mask_points)
        mask_color = generate_color_based_on_name(name)
        try:
            overlay = image.copy()
            cv2.fillPoly(overlay, [mask_points.astype(np.int32)], mask_color)
            image = cv2.addWeighted(overlay, 0.3, image, 0.7, 0)
            cv2.drawContours(
                image,
                [mask_points.astype(np.int32)],
                -1,
                color=color,
                thickness=int(8 * adjust_param),
            )

            # 绘制矩形包围框（如果启用）
            if rectangle_bbox:
                x, y, w, h = cv2.boundingRect(mask_points.astype(np.int32))
                cv2.rectangle(
                    image,
                    (x, y),
                    (x + w, y + h),
                    color=color,
                    thickness=int(5 * adjust_param),
                )

            # 计算面积、周长、圆度
            area = cv2.contourArea(mask_points.astype(np.int32))
            perimeter = cv2.arcLength(mask_points.astype(np.int32), True)
            circularity = 4 * np.pi * area / (perimeter**2) if perimeter > 0 else 0

            # 计算色彩
            mask = np.zeros(image.shape[:2], dtype=np.uint8)
            cv2.drawContours(mask, [mask_points.astype(np.int32)], -1, 255, -1)
            color_points = cv2.findNonZero(mask)
            selected_points = color_points[
                np.random.choice(color_points.shape[0], 5, replace=False)
            ]
            colors = np.mean([image[y, x] for x, y in selected_points[:, 0]], axis=0)
            color_str = f"({colors[0]:.1f}, {colors[1]:.1f}, {colors[2]:.1f})"

            # 绘制类别名称
            x, y = np.min(mask_points, axis=0).astype(int)
            image = draw_with_chinese(
                image,
                name,
                (x, y - int(30 * adjust_param)),
                font_size=int(35 * adjust_param),
                color=color,
            )
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
    if line_number is not None and not is_api:
        x1, y1, x2, y2 = bbox
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)
        image = draw_with_chinese(
            image,
            str(line_number),
            (center_x, center_y),
            font_size=int(20 * adjust_param),
            color=color,
        )

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
        (1.0, (255, 255, 0)),  # 最高温度：黄色
    ]

    # 创建自定义颜色映射
    colors = sorted(
        [(pos, tuple(np.array(color) / 255)) for pos, color in colors],
        key=lambda x: x[0],
    )
    colormap = LinearSegmentedColormap.from_list(
        "custom", [(pos, color) for pos, color in colors]
    )

    # 将图像转换为灰度图像
    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 将图像转换为 NumPy 数组
    img_array = np.array(image)

    # 应用对比度和亮度调整
    img_array = np.clip(
        img_array.astype(np.float32) * contrast + brightness, 0, 255
    ).astype(np.uint8)

    # 应用颜色映射
    colored_array = colormap(img_array / 255.0)[:, :, :3]  # 忽略alpha通道
    colored_array = (colored_array * 255).astype(np.uint8)

    return cv2.cvtColor(colored_array, cv2.COLOR_RGB2BGR)


def is_black_and_white(image_array):
    """
    判断一个 BGR 图像是否是黑白图像。

    参数:
        image_array (numpy.ndarray): 输入的 BGR 图像数组。

    返回:
        bool: 如果图像是黑白图像，返回 True；否则返回 False。
    """
    # 检查图像是否为 BGR 格式
    if len(image_array.shape) != 3 or image_array.shape[2] != 3:
        return

    # 检查每个像素的 B、G、R 通道值是否相等
    is_bw = np.all(image_array[:, :, 0] == image_array[:, :, 1]) and np.all(
        image_array[:, :, 1] == image_array[:, :, 2]
    )

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
            undistorted = cv2.undistort(
                frame, camera_matrix, dist_coeffs, None, new_camera_mtx
            )
            # 可选：裁剪ROI
            x, y, w, h = roi
            undistorted = undistorted[y : y + h, x : x + w]
            return undistorted
        except Exception as e:
            print(f"去畸变失败: {e}")
            return frame
    return frame


def auto_undistort_image(img, k1):
    """
    根据用户提供的畸变系数对图像进行去畸变处理。

    参数：
        img (numpy.ndarray): 输入的图像。
        k1 (float): 用户提供的畸变系数。

    返回：
        numpy.ndarray: 去畸变后的图像。
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    cx, cy = w / 2, h / 2

    # Undistort image using OpenCV remap
    K = np.array([[w, 0, cx], [0, w, cy], [0, 0, 1]])  # approximate fx = fy = w
    D = np.array([k1, 0, 0, 0])  # only k1 used

    map1, map2 = cv2.initUndistortRectifyMap(K, D, None, K, (w, h), cv2.CV_32FC1)
    undistorted = cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)

    return undistorted


def rotate_image(img, angle_x, angle_y, zoom_factor=1.0):
    """
    对图像进行旋转变换并添加缩放功能。
    参数：
        img (numpy.ndarray): 输入的图像。
        angle_x (float): 绕X轴旋转的角度（单位：度）。
        angle_y (float): 绕Y轴旋转的角度（单位：度）。
        zoom_factor (float): 缩放因子。大于1表示放大，小于1表示缩小。
    返回：
        numpy.ndarray: 旋转变换后的图像。
    """
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2

    # 弧度制
    pitch = np.deg2rad(angle_x)
    roll = np.deg2rad(angle_y)

    # 构造 K
    f = 1.2 * max(h, w)
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1]])
    K_inv = np.linalg.inv(K)

    # 构造 R
    Rx = np.array(
        [
            [1, 0, 0],
            [0, np.cos(pitch), -np.sin(pitch)],
            [0, np.sin(pitch), np.cos(pitch)],
        ]
    )

    Rz = np.array(
        [[np.cos(roll), -np.sin(roll), 0], [np.sin(roll), np.cos(roll), 0], [0, 0, 1]]
    )
    R = Rz @ Rx

    # 透视矩阵 H
    H = K @ R @ K_inv

    # 计算原图中心变换后的位置
    orig_center = np.array([[cx], [cy], [1]])
    new_center = H @ orig_center
    new_center /= new_center[2]

    # 偏移量（让变换后图像的中心 = 原中心）
    dx = cx - new_center[0, 0]
    dy = cy - new_center[1, 0]

    # 构造平移矩阵 T
    T = np.array([[1, 0, dx], [0, 1, dy], [0, 0, 1]])

    # 加入平移补偿后的新变换矩阵
    H_corrected = T @ H

    # 应用变换
    result = cv2.warpPerspective(img, H_corrected, (w, h), flags=cv2.INTER_LINEAR)

    # 缩放处理
    if zoom_factor > 1.0:  # 放大
        new_w, new_h = int(w / zoom_factor), int(h / zoom_factor)
        x1, y1 = (w - new_w) // 2, (h - new_h) // 2
        x2, y2 = x1 + new_w, y1 + new_h
        result = result[y1:y2, x1:x2]
    elif zoom_factor < 1.0:  # 缩小
        new_w, new_h = int(w * zoom_factor), int(h * zoom_factor)
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pad_w, pad_h = (w - new_w) // 2, (h - new_h) // 2
        result = cv2.copyMakeBorder(
            result, pad_h, pad_h, pad_w, pad_w, cv2.BORDER_CONSTANT, value=[0, 0, 0]
        )

    return result


def order_points(pts):
    """
    对四边形四个点进行排序：左上、右上、右下、左下。
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]  # top-left
    rect[2] = pts[np.argmax(s)]  # bottom-right
    rect[1] = pts[np.argmin(diff)]  # top-right
    rect[3] = pts[np.argmax(diff)]  # bottom-left
    return rect


def find_largest_valid_contour(image, scale_factor=0.1):
    """
    查找面积最大的有效轮廓。

    Args:
        image (numpy.ndarray): 输入图像。
        scale_factor (float): 有效区域最小面积占比。

    Returns:
        np.ndarray or None: 面积最大的有效轮廓点集，若无则返回 None。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = image.shape[:2]
    min_area = h * w * scale_factor

    # 过滤出所有满足面积的轮廓
    valid_cnts = [cnt for cnt in contours if cv2.contourArea(cnt) >= min_area]
    if not valid_cnts:
        return None
    largest_cnt = max(valid_cnts, key=cv2.contourArea)
    return largest_cnt


def auto_keystone_correction(image, scale_factor=0.1, output_path=None):
    """
    自动梯形矫正，支持多个相邻区域合并处理。

    Args:
        image (numpy.ndarray): 输入图像。
        scale_factor (float): 有效区域最小面积占比。
        output_path (str): 可选，输出保存路径。

    Returns:
        numpy.ndarray: 矫正后的图像。
    """
    largest_cnt = find_largest_valid_contour(image, scale_factor)
    if largest_cnt is None:
        print("[警告] 未检测到有效边界，返回原图")
        return image

    # 使用 approxPolyDP 获取逼近的四边形
    epsilon = 0.02 * cv2.arcLength(largest_cnt, True)
    approx = cv2.approxPolyDP(largest_cnt, epsilon, True)
    if len(approx) == 4:  # 如果逼近结果是四边形
        box = approx.reshape(4, 2)
        box = order_points(box)
    else:
        print("[警告] 未检测到梯形，返回原图")
        return image

    # 计算目标宽高（保持比例）
    (tl, tr, br, bl) = box
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)

    maxWidth = int(max(widthA, widthB))
    maxHeight = int(max(heightA, heightB))

    dst_pts = np.array(
        [[0, 0], [maxWidth - 1, 0], [maxWidth - 1, maxHeight - 1], [0, maxHeight - 1]],
        dtype="float32",
    )

    # 透视变换
    M = cv2.getPerspectiveTransform(box, dst_pts)
    corrected = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    if output_path:
        cv2.imwrite(output_path, corrected)

    return corrected


def fill_largest_polygon_white(image, scale_factor=0.1):
    """
    检测最大有效轮廓并将其外部区域填充为白色。

    Args:
        image (numpy.ndarray): 输入图像 (BGR)。
        scale_factor (float): 有效区域最小面积占比。

    Returns:
        numpy.ndarray: 填充后的图像。
    """
    largest_cnt = find_largest_valid_contour(image, scale_factor)
    if largest_cnt is None:
        print("[警告] 未检测到有效边界，返回原图")
        return image
    polygon_points = largest_cnt.reshape(-1, 2)
    mask = np.zeros(image.shape[:2], dtype=np.uint8)
    cv2.fillPoly(mask, [polygon_points.astype(np.int32)], 255)
    white_bg = np.ones_like(image, dtype=np.uint8) * 255
    result = np.where(mask[..., None] == 255, image, white_bg)
    return result


def enhance_texture(image, method="clahe"):
    """
    Enhance the texture of the input image using the specified method and return the enhanced RGB image.

    Args:
        image (numpy.ndarray): Input image in BGR format.
        method (str): Enhancement method, either "CLAHE" or "Histogram Equalization".

    Returns:
        numpy.ndarray: Enhanced image in RGB format.
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if method == "clahe":
        # Create CLAHE object
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        # Apply CLAHE
        enhanced_gray = clahe.apply(gray)
    elif method == "histogram_equalization":
        # Apply Histogram Equalization
        enhanced_gray = cv2.equalizeHist(gray)
    else:
        raise ValueError(
            "Invalid enhancement method. Choose 'CLAHE' or 'Histogram Equalization'."
        )

    # Convert the enhanced grayscale image back to RGB format
    enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)

    return enhanced_rgb


def extract_gps_info(image_path):
    """
    从图片EXIF信息中提取GPS经纬度信息

    Args:
        image_path (str): 图片文件路径

    Returns:
        dict: 包含GPS信息的字典，包括经度、纬度、高度等
    """
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)

        if not tags:
            return None

        def convert_to_degrees(value):
            """将GPS坐标转换为十进制度数"""
            if value and hasattr(value, "values") and len(value.values) == 3:
                d, m, s = [float(v.num) / float(v.den) for v in value.values]
                return d + m / 60.0 + s / 3600.0
            return None

        def get_tag(name):
            return tags.get(name)

        result = {}

        lat = get_tag("GPS GPSLatitude")
        lat_ref = get_tag("GPS GPSLatitudeRef")
        if lat and lat_ref:
            lat_val = convert_to_degrees(lat)
            if lat_val is not None:
                if str(lat_ref.values[0]).upper() == "S":
                    lat_val = -lat_val
                result["latitude"] = lat_val
                result["latitude_ref"] = str(lat_ref.values[0])

        lon = get_tag("GPS GPSLongitude")
        lon_ref = get_tag("GPS GPSLongitudeRef")
        if lon and lon_ref:
            lon_val = convert_to_degrees(lon)
            if lon_val is not None:
                if str(lon_ref.values[0]).upper() == "W":
                    lon_val = -lon_val
                result["longitude"] = lon_val
                result["longitude_ref"] = str(lon_ref.values[0])

        alt = get_tag("GPS GPSAltitude")
        alt_ref = get_tag("GPS GPSAltitudeRef")
        if alt:
            try:
                alt_value = float(alt.values[0].num) / float(alt.values[0].den)
                result["altitude"] = alt_value
                if alt_ref:
                    result["altitude_ref"] = alt_ref.values[0]
            except Exception:
                pass

        timestamp = get_tag("GPS GPSTimeStamp")
        datestamp = get_tag("GPS GPSDate")
        if timestamp:
            result["gps_timestamp"] = tuple(
                float(v.num) / float(v.den) for v in timestamp.values
            )
        if datestamp:
            result["gps_datestamp"] = str(datestamp)

        return result if result else None

    except Exception as e:
        print(f"提取GPS信息时出错: {e}")
        return None


def format_gps_info(gps_info):
    """
    格式化GPS信息为可读的字符串

    Args:
        gps_info (dict): GPS信息字典

    Returns:
        str: 格式化后的GPS信息字符串
    """
    if not gps_info:
        return "未找到GPS信息"

    parts = []

    # 格式化纬度
    if "latitude" in gps_info:
        lat_str = f"{gps_info['latitude']:.6f}°"
        if "latitude_ref" in gps_info:
            lat_str += f" {gps_info['latitude_ref']}"
        parts.append(f"纬度: {lat_str}")

    # 格式化经度
    if "longitude" in gps_info:
        lon_str = f"{gps_info['longitude']:.6f}°"
        if "longitude_ref" in gps_info:
            lon_str += f" {gps_info['longitude_ref']}"
        parts.append(f"经度: {lon_str}")

    # 格式化高度
    if "altitude" in gps_info:
        alt_str = f"{gps_info['altitude']:.1f}m"
        if "altitude_ref" in gps_info:
            if gps_info["altitude_ref"] == 1:
                alt_str += " (海平面以下)"
            else:
                alt_str += " (海平面以上)"
        parts.append(f"高度: {alt_str}")

    # 格式化时间戳
    if "gps_timestamp" in gps_info and "gps_datestamp" in gps_info:
        timestamp = gps_info["gps_timestamp"]
        datestamp = gps_info["gps_datestamp"]
        if isinstance(timestamp, tuple) and len(timestamp) == 3:
            time_str = f"{int(timestamp[0]):02d}:{int(timestamp[1]):02d}:{int(timestamp[2]):02d}"
            parts.append(f"GPS时间: {datestamp} {time_str}")

    return "\n".join(parts) if parts else "GPS信息不完整"


def compute_inclusion_relations(detections):
    """计算组串与单组件的包含关系."""
    strings = []
    components = []
    for idx, det in enumerate(detections):
        if len(det) < 3:
            continue
        name = det[0]
        bbox = det[2]
        if name == "string":
            strings.append((idx, bbox))
        elif name == "component":
            components.append((idx, bbox))

    records = []
    for s_idx, s_bbox in strings:
        x1_s, y1_s, x2_s, y2_s = s_bbox
        count = 0
        for _, c_bbox in components:
            x1_c, y1_c, x2_c, y2_c = c_bbox
            if x1_c >= x1_s and y1_c >= y1_s and x2_c <= x2_s and y2_c <= y2_s:
                count += 1
        records.append([f"string_{s_idx}", count])

    return pd.DataFrame(records, columns=["组串编号", "包含组件数"])
