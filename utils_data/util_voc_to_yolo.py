import os
import xml.etree.ElementTree as ET
from shutil import copy2
from PIL import Image
import random

# === Configuration ===
xml_folder = "可见光xml"
img_folder = "可见光jpg"
output_base = "yolo_dataset"

# Define your class names
CLASSES = ['yyzd', 'ygfs', 'zw', 'yyzd_zw', 'ns', 'yyzd_ns', 'zw_ns', 'gfbzjbx', 'gfbqs', 'mbsl', 'snow', 'crack']

# Create output subfolders
for subset in ['train', 'test']:
    os.makedirs(os.path.join(output_base, "images", subset), exist_ok=True)
    os.makedirs(os.path.join(output_base, "labels", subset), exist_ok=True)

def find_image_file(filename):
    """Try to resolve the correct image file by extension"""
    name_wo_ext = os.path.splitext(filename)[0]
    for ext in ['.jpg', '.jpeg', '.JPG', '.png']:
        candidate = os.path.join(img_folder, name_wo_ext + ext)
        if os.path.exists(candidate):
            return os.path.basename(candidate)
    return None

def convert_voc_to_yolo(xml_file_path):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    raw_img_name = root.find('filename').text.strip()
    img_name = find_image_file(raw_img_name)

    if img_name is None:
        print(f"[跳过] 找不到对应图像文件: {raw_img_name}")
        return None, None

    image_path = os.path.join(img_folder, img_name)
    image = Image.open(image_path)
    img_width, img_height = image.size

    yolo_annotations = []

    for obj in root.findall('object'):
        class_name = obj.find('name').text.strip()
        if class_name not in CLASSES:
            print(f"[跳过] 未知类别: {class_name} in {xml_file_path}")
            continue
        class_id = CLASSES.index(class_name)

        bbox = obj.find('bndbox')
        xmin = float(bbox.find('xmin').text)
        ymin = float(bbox.find('ymin').text)
        xmax = float(bbox.find('xmax').text)
        ymax = float(bbox.find('ymax').text)

        x_center = ((xmin + xmax) / 2.0) / img_width
        y_center = ((ymin + ymax) / 2.0) / img_height
        width = (xmax - xmin) / img_width
        height = (ymax - ymin) / img_height

        yolo_annotations.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

    return img_name, yolo_annotations

# === Main split and conversion ===

# Collect all valid XML files
xml_files = [f for f in os.listdir(xml_folder) if f.endswith('.xml')]
random.shuffle(xml_files)

split_idx = int(len(xml_files) * 0.8)
train_xmls = xml_files[:split_idx]
test_xmls = xml_files[split_idx:]

def process_subset(xml_list, subset):
    for xml_file in xml_list:
        xml_path = os.path.join(xml_folder, xml_file)
        img_name, yolo_lines = convert_voc_to_yolo(xml_path)

        if img_name is None or yolo_lines is None:
            continue

        # Copy image
        src_img_path = os.path.join(img_folder, img_name)
        dst_img_path = os.path.join(output_base, "images", subset, img_name)
        copy2(src_img_path, dst_img_path)

        # Write label
        label_file = os.path.splitext(img_name)[0] + ".txt"
        dst_lbl_path = os.path.join(output_base, "labels", subset, label_file)
        with open(dst_lbl_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(yolo_lines))

# Process train and test sets
process_subset(train_xmls, 'train')
process_subset(test_xmls, 'test')

print("✅ Dataset split and VOC to YOLO conversion finished.")
