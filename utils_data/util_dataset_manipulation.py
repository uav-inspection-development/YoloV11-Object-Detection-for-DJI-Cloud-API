import os
import cv2
import re
import argparse
from pathlib import Path
from tqdm import tqdm

"此脚本需要在数据集转换脚本执行后后执行"

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


def main(source_folder, target_width=720, target_height=480):
    if not os.path.exists(source_folder):
        print("指定的源文件夹不存在！")
        exit()

    resized_images_folder = os.path.join(source_folder, "resized_images")
    resized_labels_folder = os.path.join(source_folder, "resized_labels")
    os.makedirs(resized_images_folder, exist_ok=True)
    os.makedirs(resized_labels_folder, exist_ok=True)

    subfolders = ["train", "test", "val"]

    for subfolder in subfolders:
        images_subfolder = os.path.join(source_folder, "images", subfolder)
        labels_subfolder = os.path.join(source_folder, "labels", subfolder)

        if not os.path.exists(images_subfolder):
            print(f"图像子文件夹 '{images_subfolder}' 不存在，跳过")
            continue

        if not os.path.exists(labels_subfolder):
            print(f"标签子文件夹 '{labels_subfolder}' 不存在，跳过")
            continue

        resized_images_subfolder = os.path.join(resized_images_folder, subfolder)
        resized_labels_subfolder = os.path.join(resized_labels_folder, subfolder)
        os.makedirs(resized_images_subfolder, exist_ok=True)
        os.makedirs(resized_labels_subfolder, exist_ok=True)

        image_files = list(Path(images_subfolder).glob("*"))
        label_files = list(Path(labels_subfolder).glob("*.txt"))

        if len(image_files) != len(label_files):
            print(f"图像文件和标签文件数量不一致，跳过子文件夹 '{subfolder}'")
            continue

        for image_file, label_file in tqdm(zip(image_files, label_files), total=len(image_files), desc=f"处理{subfolder}集", unit="对"):
            if image_file.stem != label_file.stem:
                continue

            new_image_filename = remove_chinese_chars_and_symbols(image_file.name)
            new_label_filename = remove_chinese_chars_and_symbols(label_file.name)

            new_image_filename = ensure_unique_filename(images_subfolder, new_image_filename)
            new_label_filename = ensure_unique_filename(labels_subfolder, new_label_filename)

            new_image_file = os.path.join(images_subfolder, new_image_filename)
            new_label_file = os.path.join(labels_subfolder, new_label_filename)

            os.rename(image_file, new_image_file)
            os.rename(label_file, new_label_file)

            if not os.path.exists(new_image_file):
                print(f"图像文件不存在: {new_image_file}")
                continue

            image = cv2.imread(str(new_image_file))
            if image is None:
                print(f"无法读取图像文件: {new_image_file}")
                continue

            resized_image = cv2.resize(image, (target_width, target_height))
            save_image_path = os.path.join(resized_images_subfolder, new_image_filename)
            cv2.imwrite(save_image_path, resized_image)

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

            save_label_path = os.path.join(resized_labels_subfolder, new_label_filename)
            with open(save_label_path, 'w') as f:
                f.writelines(adjusted_lines)

    print("\n所有图像和标签调整大小完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Resize YOLO dataset images and labels, and clean file names.")
    parser.add_argument("--source_folder", required=True, help="包含 images 和 labels 文件夹的源文件夹路径")
    parser.add_argument("--target_width", type=int, default=720, help="目标宽度，默认720")
    parser.add_argument("--target_height", type=int, default=480, help="目标高度，默认480")
    args = parser.parse_args()

    main(args.source_folder, args.target_width, args.target_height)
