import os
import cv2
import numpy as np
import argparse
from pathlib import Path


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

    for label in labels:
        class_id = label[0]
        x_center, y_center, bbox_width, bbox_height = map(float, label[1:5])
        points = np.array(label[5:], dtype=np.float32).reshape(-1, 2)

        x_center = int(x_center * width)
        y_center = int(y_center * height)
        bbox_width = int(bbox_width * width)
        bbox_height = int(bbox_height * height)

        x_min = x_center - bbox_width // 2
        y_min = y_center - bbox_height // 2
        x_max = x_center + bbox_width // 2
        y_max = y_center + bbox_height // 2

        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        points[:, 0] = (points[:, 0] * width).astype(int)
        points[:, 1] = (points[:, 1] * height).astype(int)
        points = points.reshape((-1, 1, 2)).astype(np.int32)
        cv2.polylines(image, [points], isClosed=True, color=(0, 0, 255), thickness=2)

        cv2.putText(image, f"Class {class_id}", (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

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
        for image_file in image_files:
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
