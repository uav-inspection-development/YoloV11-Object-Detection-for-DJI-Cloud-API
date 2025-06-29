import os
import cv2
import numpy as np
import argparse
from pathlib import Path
from tqdm import tqdm


def draw_labels(image_path, label_path, output_path):
    """绘制 YOLO 标签的边界框和多边形，并保存可视化结果"""
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法加载图像：{image_path}")
        return

    height, width, _ = image.shape

    if not os.path.exists(label_path):
        print(f"标注文件不存在：{label_path}")
        return

    with open(label_path, 'r') as f:
        labels = [line.strip().split() for line in f.readlines()]

    # 定义类别颜色映射（可根据类别数扩展）
    color_map = [
        (0, 0, 255),    # 红
        (0, 255, 0)     # 绿
    ]

    for label in labels:
        class_id = int(label[0])
        color = color_map[class_id % len(color_map)]
        # 直接取后面的所有点
        points = np.array(label[1:], dtype=np.float32).reshape(-1, 2)
        points[:, 0] = (points[:, 0] * width).astype(int)
        points[:, 1] = (points[:, 1] * height).astype(int)
        points_int = points.astype(np.int32).reshape((-1, 1, 2))

        # 画多边形
        cv2.polylines(image, [points_int], isClosed=True, color=color, thickness=2)

        # 计算bbox
        x_min, y_min = int(points[:, 0].min()), int(points[:, 1].min())
        x_max, y_max = int(points[:, 0].max()), int(points[:, 1].max())
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, 2)

        cv2.putText(image, f"Class {class_id}", (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    cv2.imwrite(output_path, image)
    print(f"保存绘制后的图像到：{output_path}")


def main(source_folder, output_folder):
    if not os.path.exists(source_folder):
        print("指定的源文件夹不存在！")
        exit()

    os.makedirs(output_folder, exist_ok=True)

    subfolders = ["train", "val", "test"]

    for subfolder in subfolders:
        images_subfolder = os.path.join(source_folder, "images", subfolder)
        labels_subfolder = os.path.join(source_folder, "labels", subfolder)

        if not os.path.exists(images_subfolder):
            print(f"图像子文件夹 '{images_subfolder}' 不存在，跳过")
            continue

        if not os.path.exists(labels_subfolder):
            print(f"标签子文件夹 '{labels_subfolder}' 不存在，跳过")
            continue

        visualization_subfolder = os.path.join(output_folder, subfolder)
        os.makedirs(visualization_subfolder, exist_ok=True)

        image_files = list(Path(images_subfolder).glob("*.jpg")) + list(Path(images_subfolder).glob("*.png"))
        for image_file in tqdm(image_files, desc=f"处理{subfolder}集", unit="张"):
            image_path = str(image_file)
            txt_path = str(Path(labels_subfolder) / f"{image_file.stem}.txt")
            output_path = os.path.join(visualization_subfolder, f"{image_file.stem}_visualized.jpg")

            draw_labels(image_path, txt_path, output_path)

    print("\n所有文件可视化完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualize YOLO labels (bounding boxes and polygons) on images.")
    parser.add_argument("--source_folder", required=True, help="源文件夹路径，包含 images 和 labels 文件夹")
    parser.add_argument("--output_folder", required=True, help="目标输出文件夹路径，用于保存可视化结果")
    args = parser.parse_args()

    main(args.source_folder, args.output_folder)
