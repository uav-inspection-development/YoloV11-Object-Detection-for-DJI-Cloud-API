import os
import re
import argparse
import shutil
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


def main(source_folder, output_folder=None):
    if not os.path.exists(source_folder):
        print("指定的源文件夹不存在！")
        exit()
    
    # 如果没有指定输出文件夹，则在源文件夹同级目录创建带_cleaned后缀的文件夹
    if output_folder is None:
        source_folder_name = os.path.basename(os.path.abspath(source_folder))
        parent_dir = os.path.dirname(os.path.abspath(source_folder))
        output_folder = os.path.join(parent_dir, f"{source_folder_name}_cleaned")
    
    # 创建输出文件夹结构
    os.makedirs(output_folder, exist_ok=True)
    output_images_folder = os.path.join(output_folder, "images")
    output_labels_folder = os.path.join(output_folder, "labels")
    os.makedirs(output_images_folder, exist_ok=True)
    os.makedirs(output_labels_folder, exist_ok=True)

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

        # 创建输出子文件夹
        output_images_subfolder = os.path.join(output_images_folder, subfolder)
        output_labels_subfolder = os.path.join(output_labels_folder, subfolder)
        os.makedirs(output_images_subfolder, exist_ok=True)
        os.makedirs(output_labels_subfolder, exist_ok=True)

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

            new_image_filename = ensure_unique_filename(output_images_subfolder, new_image_filename)
            new_label_filename = ensure_unique_filename(output_labels_subfolder, new_label_filename)

            new_image_file = os.path.join(output_images_subfolder, new_image_filename)
            new_label_file = os.path.join(output_labels_subfolder, new_label_filename)

            # 复制文件到输出文件夹
            shutil.copy2(image_file, new_image_file)
            shutil.copy2(label_file, new_label_file)

    print(f"\n文件名清理完成！输出文件夹: {output_folder}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean file names by removing Chinese characters and symbols from YOLO dataset.")
    parser.add_argument("--source_folder", required=True, help="包含 images 和 labels 文件夹的源文件夹路径")
    parser.add_argument("--output_folder", help="输出文件夹路径（可选，默认在源文件夹下创建cleaned文件夹）")
    args = parser.parse_args()

    main(args.source_folder, args.output_folder)
