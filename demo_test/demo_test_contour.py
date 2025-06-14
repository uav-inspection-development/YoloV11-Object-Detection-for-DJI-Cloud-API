import cv2
import numpy as np

def draw_string_borders(image_path, min_area=5000, output_path=None):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 增强图像对比度
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_gray = clahe.apply(gray)

    # 使用自适应阈值进行二值化
    adaptive_thresh = cv2.adaptiveThreshold(
        enhanced_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blockSize=15, C=5
    )

    # 膨胀操作以连接边缘
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(adaptive_thresh, kernel, iterations=2)

    # 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            # 检测最小外接矩形
            rect = cv2.minAreaRect(cnt)
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # 对点进行排序：左上、右上、右下、左下
            sorted_box = order_points(box)

            # 计算目标宽高（保持比例）
            (tl, tr, br, bl) = sorted_box
            widthA = np.linalg.norm(br - bl)
            widthB = np.linalg.norm(tr - tl)
            heightA = np.linalg.norm(tr - br)
            heightB = np.linalg.norm(tl - bl)

            maxWidth = int(max(widthA, widthB))
            maxHeight = int(max(heightA, heightB))

            # 定义目标矩形
            dst_pts = np.array([
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1]
            ], dtype="float32")

            # 透视变换
            M = cv2.getPerspectiveTransform(sorted_box, dst_pts)
            corrected = cv2.warpPerspective(img, M, (maxWidth, maxHeight))

            # 绘制矫正后的轮廓
            cv2.drawContours(img, [np.int0(sorted_box)], 0, (0, 255, 0), 3)

    # 保存结果并显示
    if output_path:
        cv2.imwrite(output_path, img)
    cv2.imshow("String Borders", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

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

# 用法示例
if __name__ == "__main__":
    draw_string_borders("MA04210710108352.JPG", min_area=100000, output_path="EL_test_002_result.jpg")