import os
import random
import numpy as np
from PIL import Image, ImageEnhance
from pathlib import Path

# 指定源文件夹路径
source_folder = input("请输入包含 images 和 labels 文件夹的源文件夹路径：").strip()

# 检查源文件夹是否存在
if not os.path.exists(source_folder):
    print("指定的源文件夹不存在！")
    exit()

# 创建增强后的数据存储文件夹（如果不存在）
augmented_folder = os.path.join(source_folder, "augmented_data")
os.makedirs(augmented_folder, exist_ok=True)

# 创建增强后的图像和标注文件夹
augmented_images_folder = os.path.join(augmented_folder, "images")
augmented_labels_folder = os.path.join(augmented_folder, "labels")
os.makedirs(augmented_images_folder, exist_ok=True)
os.makedirs(augmented_labels_folder, exist_ok=True)

# 固定图像尺寸
target_width = 720
target_height = 480

# 遍历 train, val, test 子文件夹
subfolders = ["train", "val", "test"]

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

    # 创建增强后的子文件夹
    augmented_images_subfolder = os.path.join(augmented_images_folder, subfolder)
    augmented_labels_subfolder = os.path.join(augmented_labels_folder, subfolder)
    os.makedirs(augmented_images_subfolder, exist_ok=True)
    os.makedirs(augmented_labels_subfolder, exist_ok=True)

    # 遍历子文件夹中的图像文件
    image_files = list(Path(images_subfolder).glob("*.jpg")) + list(Path(images_subfolder).glob("*.png"))
    for image_file in image_files:
        image_path = str(image_file)
        txt_path = str(Path(labels_subfolder) / f"{image_file.stem}.txt")

        # 检查对应的标注文件是否存在
        if not os.path.exists(txt_path):
            print(f"警告：未找到对应的标注文件 {txt_path}，跳过图像 {image_path}")
            continue

        # 加载图像
        image = Image.open(image_path)
        original_width, original_height = image.size

        # 读取标注文件
        with open(txt_path, 'r') as f:
            labels = [line.strip().split() for line in f.readlines()]

        # 将原图像和标注文件复制到增强后的文件夹中
        original_image_path = os.path.join(augmented_images_subfolder, f"{image_file.stem}.jpg")
        original_txt_path = os.path.join(augmented_labels_subfolder, f"{image_file.stem}.txt")
        image.save(original_image_path)
        with open(original_txt_path, 'w') as f:
            for label in labels:
                line = " ".join(label)
                f.write(line + "\n")

        # 对每张图像生成10个增强版本
        for i in range(10):
            # 随机缩放
            scale_factor = random.uniform(0.5, 1.5)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)
            image_resized = image.resize((new_width, new_height))

            # 随机旋转
            angle = random.uniform(-180, 180)  # 旋转角度范围为-180到180度
            image_rotated = image_resized.rotate(angle, expand=True)
            rotated_width, rotated_height = image_rotated.size

            # 随机亮度调整
            enhancer = ImageEnhance.Brightness(image_rotated)
            brightness_factor = random.uniform(0.6, 1.4)
            image_augmented = enhancer.enhance(brightness_factor)

            # 调整图像大小到目标尺寸
            image_final = image_augmented.resize((target_width, target_height))

            # 调整标注点
            augmented_labels = []
            for label in labels:
                class_id = label[0]
                x_center, y_center, bbox_width, bbox_height = map(float, label[1:5])
                points = np.array(label[5:], dtype=np.float32).reshape(-1, 2)

                # 缩放
                x_center *= scale_factor
                y_center *= scale_factor
                bbox_width *= scale_factor
                bbox_height *= scale_factor
                points[:, 0] *= scale_factor
                points[:, 1] *= scale_factor

                # 旋转
                center = np.array([new_width / 2, new_height / 2])
                rotation_matrix = np.array([
                    [np.cos(np.deg2rad(angle)), -np.sin(np.deg2rad(angle))],
                    [np.sin(np.deg2rad(angle)), np.cos(np.deg2rad(angle))]
                ])
                points = np.dot(points - center, rotation_matrix) + center

                # 调整到目标尺寸
                x_center = x_center / rotated_width * target_width
                y_center = y_center / rotated_height * target_height
                bbox_width = bbox_width / rotated_width * target_width
                bbox_height = bbox_height / rotated_height * target_height
                points[:, 0] = points[:, 0] / rotated_width * target_width
                points[:, 1] = points[:, 1] / rotated_height * target_height

                # 归一化到 [0, 1]
                x_center /= target_width
                y_center /= target_height
                bbox_width /= target_width
                bbox_height /= target_height
                points[:, 0] /= target_width
                points[:, 1] /= target_height

                # 生成新的标注行
                new_label = [class_id, x_center, y_center, bbox_width, bbox_height] + points.flatten().tolist()
                augmented_labels.append(new_label)

            # 保存增强后的图像
            augmented_image_path = os.path.join(augmented_images_subfolder, f"{image_file.stem}_{i}.jpg")
            image_final.save(augmented_image_path)

            # 保存增强后的标注文件
            augmented_txt_path = os.path.join(augmented_labels_subfolder, f"{image_file.stem}_{i}.txt")
            with open(augmented_txt_path, 'w') as f:
                for label in augmented_labels:
                    line = " ".join(map(str, label))
                    f.write(line + "\n")

            print(f"增强后的图像和标注已保存：{augmented_image_path} 和 {augmented_txt_path}")

print("\n所有文件增强完成！")