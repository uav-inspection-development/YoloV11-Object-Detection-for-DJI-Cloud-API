import os
import shutil
import random

"这段代码是一个用于组织图像和对应XML标签文件的Python脚本。"
"它的主要功能是将图像文件和XML文件从一个源文件夹中提取出来，"
"并按照是否有标签（XML文件）以及训练集、测试集和验证集的比例分配到不同的目标文件夹中。"

# 源文件夹路径
source_folder = input("请输入包含图像和XML文件的源文件夹路径：").strip()

# 创建目标文件夹
target_folder = os.path.join(source_folder, "organized_data")
os.makedirs(target_folder, exist_ok=True)

trash_folder = os.path.join(target_folder, "trash")
images_folder = os.path.join(target_folder, "images")
labels_folder = os.path.join(target_folder, "labels")

os.makedirs(trash_folder, exist_ok=True)
os.makedirs(images_folder, exist_ok=True)
os.makedirs(labels_folder, exist_ok=True)

# 创建子文件夹
subfolders = ["train", "test", "val"]
for subfolder in subfolders:
    os.makedirs(os.path.join(images_folder, subfolder), exist_ok=True)
    os.makedirs(os.path.join(labels_folder, subfolder), exist_ok=True)

# 获取所有图像文件
image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]
image_files = []
for file in os.listdir(source_folder):
    if any(file.lower().endswith(ext) for ext in image_extensions):
        image_files.append(file)

print(f"共找到 {len(image_files)} 张图像文件")

# 将图像分为有标签和无标签
labeled_images = []
unlabeled_images = []

for image_file in image_files:
    base_name = os.path.splitext(image_file)[0]
    xml_file = base_name + ".xml"
    if os.path.exists(os.path.join(source_folder, xml_file)):
        labeled_images.append(image_file)
    else:
        unlabeled_images.append(image_file)

print(f"有标签图像数量: {len(labeled_images)}")
print(f"无标签图像数量: {len(unlabeled_images)}")

# 移动未标注的图像到trash文件夹
for i, image_file in enumerate(unlabeled_images):
    src_path = os.path.join(source_folder, image_file)
    dst_path = os.path.join(trash_folder, image_file)
    shutil.move(src_path, dst_path)
    print(f"移动未标注图像 ({i + 1}/{len(unlabeled_images)}): {image_file} → {trash_folder}")

# 按比例分配标签图像到train、test、val
random.shuffle(labeled_images)

total_labeled = len(labeled_images)
train_size = int(total_labeled * 0.8)
test_size = int(total_labeled * 0.1)

train_images = labeled_images[:train_size]
test_images = labeled_images[train_size:train_size + test_size]
val_images = labeled_images[train_size + test_size:]

print(f"训练集分配: {len(train_images)} 张图像")
print(f"测试集分配: {len(test_images)} 张图像")
print(f"验证集分配: {len(val_images)} 张图像")

# 移动训练集图像和对应的XML文件
for i, image_file in enumerate(train_images):
    base_name = os.path.splitext(image_file)[0]
    xml_file = base_name + ".xml"

    src_image_path = os.path.join(source_folder, image_file)
    dst_image_path = os.path.join(images_folder, "train", image_file)

    src_xml_path = os.path.join(source_folder, xml_file)
    dst_xml_path = os.path.join(labels_folder, "train", xml_file)

    shutil.move(src_image_path, dst_image_path)
    shutil.move(src_xml_path, dst_xml_path)

    print(f"移动训练集图像和标签 ({i + 1}/{len(train_images)}): {image_file} → train")

# 移动测试集图像和对应的XML文件
for i, image_file in enumerate(test_images):
    base_name = os.path.splitext(image_file)[0]
    xml_file = base_name + ".xml"

    src_image_path = os.path.join(source_folder, image_file)
    dst_image_path = os.path.join(images_folder, "test", image_file)

    src_xml_path = os.path.join(source_folder, xml_file)
    dst_xml_path = os.path.join(labels_folder, "test", xml_file)

    shutil.move(src_image_path, dst_image_path)
    shutil.move(src_xml_path, dst_xml_path)

    print(f"移动测试集图像和标签 ({i + 1}/{len(test_images)}): {image_file} → test")

# 移动验证集图像和对应的XML文件
for i, image_file in enumerate(val_images):
    base_name = os.path.splitext(image_file)[0]
    xml_file = base_name + ".xml"

    src_image_path = os.path.join(source_folder, image_file)
    dst_image_path = os.path.join(images_folder, "val", image_file)

    src_xml_path = os.path.join(source_folder, xml_file)
    dst_xml_path = os.path.join(labels_folder, "val", xml_file)

    shutil.move(src_image_path, dst_image_path)
    shutil.move(src_xml_path, dst_xml_path)

    print(f"移动验证集图像和标签 ({i + 1}/{len(val_images)}): {image_file} → val")

print("\n文件组织完成！")