import cv2
import numpy as np

def draw_string_borders(image_path, min_area=5000, output_path=None):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Image file not found: {image_path}")

    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 使用中值滤波去除噪声
    denoised = cv2.medianBlur(gray, 5)
    cv2.imshow("Denoised Image", denoised)
    cv2.imwrite("step1_denoised.jpg", denoised)  # 保存去噪后的图像

    # 使用自适应阈值进行二值化
    adaptive_thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, blockSize=11, C=2
    )
    cv2.imshow("Adaptive Threshold", adaptive_thresh)
    cv2.imwrite("step2_adaptive_thresh.jpg", adaptive_thresh)  # 保存二值化图像

    # 膨胀操作以连接边缘
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(adaptive_thresh, kernel, iterations=2)
    cv2.imshow("Dilated Image", dilated)
    cv2.imwrite("step3_dilated.jpg", dilated)  # 保存膨胀图像

    # 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            if len(approx) == 4:  # 检测矩形边框
                cv2.polylines(img, [approx], isClosed=True, color=(0, 0, 255), thickness=3)

    # 保存结果并显示
    if output_path:
        cv2.imwrite(output_path, img)
    cv2.imshow("String Borders", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# 用法示例
if __name__ == "__main__":
    draw_string_borders("MA04210710108352.JPG", min_area=100000, output_path="EL_test_002_result.jpg")