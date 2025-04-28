from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import tempfile
import os
class PseudoColorizer:
    def __init__(self):
        """
        初始化伪彩色映射器
        :param colors: 包含元组的列表，格式为[(位置, (R, G, B)), ...]
                       位置范围0.0-1.0，颜色分量范围0-255
        """
        self.colors= [
        (0.0, (128, 128, 128)),  # 最低温度：黑色
        (0.3, (128, 0, 128)),  # 低温温度：紫色
        (0.8, (255, 50, 0)),  # 高温区域：红色
        (1.0, (255, 255, 0))  # 最高温度：黄色
    ]
        self.colormap = self.create_custom_colormap(self.colors)


    def create_custom_colormap(self, colors):
        """
        创建自定义颜色映射
        :return: 自定义的Colormap对象
        """
        # 归一化颜色并排序
        colors = sorted([(pos, tuple(np.array(color) / 255)) for pos, color in colors], key=lambda x: x[0])
        return LinearSegmentedColormap.from_list("custom", [(pos, color) for pos, color in colors])

    def is_grayscale(self, image):
        """
        判断图像是否为单通道灰度图
        :param image: PIL图像对象
        :return: 布尔值，True表示是灰度图，False表示不是
        """
        return image.mode == 'L'

    def apply_colormap(self, image, contrast=1.0, brightness=0):
        """
        应用伪彩色映射到图像
        :param image: PIL图像对象
        :param contrast: 对比度调整（默认1.0）
        :param brightness: 亮度调整（范围-255到255）
        :return: 伪彩色图像的PIL对象
        """
        image = Image.open(image)
        img_array = np.array(image)
        if self.is_grayscale(image):

            # 调整对比度和亮度
            # img_array = np.clip(img_array.astype(np.float32) * contrast + brightness, 0, 255).astype(np.uint8)
            # 应用颜色映射

            colored_array = self.colormap(img_array / 255.0)[:, :, :3]  # 忽略alpha通道
            colored_array = (colored_array * 255).astype(np.uint8)
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext('uploaded_file')[1]) as tmpfile:
                # 保存 PIL Image 对象到临时文件
                img_th=image.save(tmpfile.name)
                os.unlink(tmpfile.name)

            # 返回伪彩色图像
            return img_th
        else:
            print("图像不是灰度图，不能应用伪彩色映射")
            return None


# ----------------- 使用示例 -----------------
if __name__ == "__main__":
    # 定义自定义颜色梯度（可自由调整）

    # 创建伪彩色映射器实例
    colorizer = PseudoColorizer(custom_colors)

    # 读取图像
    image_path = "../icon/DJI_0021.jpg"
    img = Image.open(image_path).convert('L')  # 确保图像是灰度图

    # 应用处理并返回伪彩色图像
    pseudo_colored_img = colorizer.apply_colormap(img, contrast=1.2, brightness=30)

    # 显示伪彩色图像
    if pseudo_colored_img is not None:
        pseudo_colored_img.show()