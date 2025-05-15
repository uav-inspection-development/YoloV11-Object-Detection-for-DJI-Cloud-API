import os
import cv2
import re
from pathlib import Path

def remove_chinese_chars_and_symbols(filename):
    """清除文件名中的中文字符和特定符号"""
    pattern = re.compile(r'[\u4e00-\u9fff，,]')
    return pattern.sub('', filename)

def ensure_unique_filename(directory, filename):
    """确保文件名唯一，如果重复则添加数字后缀"""
    base_name, extension = os.path.splitext(filename)
    counter = 1
    new_filename = filename
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{base_name}_{counter}{extension}"
        counter += 1
    return new_filename

# 源文件夹路径
source_folder = input("请输入包含 images 和 labels 文件夹的源文件夹路径：").strip()

# 检查源文件夹是否存在
if not os.path.exists(source_folder):
    print("指定的源文件夹不存在！")
    exit()

# 目标尺寸（宽度和高度）
target_width = 600
target_height = 400

# 创建调整大小后的图像和标签存储文件夹
resized_images_folder = os.path.join(source_folder, "resized_images")
resized_labels_folder = os.path.join(source_folder, "resized_labels")

os.makedirs(resized_images_folder, exist_ok=True)
os.makedirs(resized_labels_folder, exist_ok=True)

# 遍历 train, test, val 子文件夹
subfolders = ["train", "test", "val"]

for subfolder in subfolders:
    # 获取子文件夹的完整路径
    images_subfolder = os.path.join(source_folder, "images", subfolder)
    labels_subfolder = os.path.join(source_folder, "labels", subfolder)

    if not os.path.exists(images_subfolder):
        print(f"图像子文件夹 '{images_subfolder}' 不存在，跳过")
        continue

    if not os.path.exists(labels_subfolder):
        print(f"标签子文件夹 '{labels_subfolder}' 不存在，跳过")
        continue

    # 创建调整大小后的子文件夹
    resized_images_subfolder = os.path.join(resized_images_folder, subfolder)
    resized_labels_subfolder = os.path.join(resized_labels_folder, subfolder)

    os.makedirs(resized_images_subfolder, exist_ok=True)
    os.makedirs(resized_labels_subfolder, exist_ok=True)

    # 获取子文件夹中的所有图像文件
    image_files = list(Path(images_subfolder).glob("*"))
    label_files = list(Path(labels_subfolder).glob("*.txt"))

    # 确保图像文件和标签文件数量一致
    if len(image_files) != len(label_files):
        print(f"图像文件和标签文件数量不一致，跳过子文件夹 '{subfolder}'")
        continue

    # 遍历图像和标签文件
    for image_file, label_file in zip(image_files, label_files):
        # 检查文件名是否匹配
        if image_file.stem != label_file.stem:
            continue

        # 清除文件名中的中文字符和特定符号
        new_image_filename = remove_chinese_chars_and_symbols(image_file.name)
        new_label_filename = remove_chinese_chars_and_symbols(label_file.name)

        # 确保文件名唯一
        new_image_filename = ensure_unique_filename(images_subfolder, new_image_filename)
        new_label_filename = ensure_unique_filename(labels_subfolder, new_label_filename)

        # 新的文件路径
        new_image_file = os.path.join(images_subfolder, new_image_filename)
        new_label_file = os.path.join(labels_subfolder, new_label_filename)

        # 重命名文件
        os.rename(image_file, new_image_file)
        os.rename(label_file, new_label_file)

        # 检查图像文件是否存在
        if not os.path.exists(new_image_file):
            print(f"图像文件不存在: {new_image_file}")
            continue

        # 读取图像
        image = cv2.imread(str(new_image_file))
        if image is None:
            print(f"无法读取图像文件: {new_image_file}")
            continue  # 跳过无法读取的图像文件

        # 获取图像原始尺寸
        original_height, original_width = image.shape[:2]

        # 计算缩放比例
        scale_x = target_width / original_width
        scale_y = target_height / original_height

        # 调整图像大小
        resized_image = cv2.resize(image, (target_width, target_height))

        # 保存调整大小后的图像
        save_image_path = os.path.join(resized_images_subfolder, new_image_filename)
        cv2.imwrite(save_image_path, resized_image)

        # 调整标签文件中的坐标
        with open(str(new_label_file), 'r') as f:
            lines = f.readlines()

        adjusted_lines = []
        for line in lines:
            parts = line.strip().split()
            if len(parts) < 5:
                continue

            label = parts[0]
            x_center = float(parts[1])
            y_center = float(parts[2])
            box_width = float(parts[3])
            box_height = float(parts[4])

            adjusted_line = f"{label} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}\n"
            adjusted_lines.append(adjusted_line)

        # 保存调整后的标签文件
        save_label_path = os.path.join(resized_labels_subfolder, new_label_filename)
        with open(save_label_path, 'w') as f:
            f.writelines(adjusted_lines)

        print(f"图像和标签调整大小成功: {new_image_filename} → {save_image_path}, {new_label_filename} → {save_label_path}")

print("\n所有图像和标签调整大小完成！")