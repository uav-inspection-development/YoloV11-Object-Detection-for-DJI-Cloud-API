import cv2
import numpy as np

def order_points(pts):
    """
    对四边形四个点进行排序：左上、右上、右下、左下。
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]      # top-left
    rect[2] = pts[np.argmax(s)]      # bottom-right
    rect[1] = pts[np.argmin(diff)]   # top-right
    rect[3] = pts[np.argmax(diff)]   # bottom-left
    return rect

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
        print("[警告] 未检测到有效边界，返回原图")
        return image

    # 找到面积最大的轮廓
    largest_cnt = max(valid_cnts, key=cv2.contourArea)

    # 在原图中绘制轮廓
    image_with_contours = image.copy()
    cv2.drawContours(image_with_contours, [largest_cnt], -1, (0, 255, 0), 2)

    # 使用 approxPolyDP 获取逼近的四边形
    epsilon = 0.02 * cv2.arcLength(largest_cnt, True)
    approx = cv2.approxPolyDP(largest_cnt, epsilon, True)
    if len(approx) == 4:  # 如果逼近结果是四边形
        box = approx.reshape(4, 2)
        box = order_points(box)
    else:
        print("[警告] 未检测到梯形，返回原图")
        return image_with_contours

    # 计算目标宽高（保持比例）
    (tl, tr, br, bl) = box
    widthA = np.linalg.norm(br - bl)
    widthB = np.linalg.norm(tr - tl)
    heightA = np.linalg.norm(tr - br)
    heightB = np.linalg.norm(tl - bl)

    maxWidth = int(max(widthA, widthB))
    maxHeight = int(max(heightA, heightB))

    dst_pts = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]
    ], dtype="float32")

    # 透视变换
    M = cv2.getPerspectiveTransform(box, dst_pts)
    corrected = cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    if output_path:
        cv2.imwrite(output_path, corrected)

    return corrected, image_with_contours

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
        raise ValueError("Invalid enhancement method. Choose 'CLAHE' or 'Histogram Equalization'.")

    # Convert the enhanced grayscale image back to RGB format
    enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)

    return enhanced_rgb

if __name__ == "__main__":
    # 示例：加载图像并进行梯形矫正
    input_image_path = "EL_test_001.jpg"  # 替换为实际输入图像路径
    output_image_path = "output.jpg"  # 替换为实际输出图像路径

    # 加载图像
    image = cv2.imread(input_image_path)
    if image is None:
        print(f"[错误] 无法加载图像: {input_image_path}")
    else:
        # 执行梯形矫正
        corrected_image, image_with_contours = auto_keystone_correction(image, scale_factor=0.1, output_path=output_image_path)
        print(f"[信息] 矫正后的图像已保存到: {output_image_path}")

        # 显示原始图像、绘制轮廓的图像和矫正后的图像
        cv2.imshow("Original Image", image)
        cv2.imshow("Image with Contours", image_with_contours)
        cv2.imshow("Corrected Image", corrected_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
