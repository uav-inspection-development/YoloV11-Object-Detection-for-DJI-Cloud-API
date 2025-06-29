import os
import xml.etree.ElementTree as ET
from PIL import Image
import random
import argparse
import shutil
from tqdm import tqdm


def convert_voc_to_yolo(xml_file, image_path, classes):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    image = Image.open(image_path)
    w, h = image.size
    yolo_lines = []

    for obj in root.findall("object"):
        name = obj.find("name").text.strip()
        if name not in classes:
            print(f"[跳过] 未知类别: {name}")
            continue
        cls_id = classes.index(name)

        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)

        x_center = (xmin + xmax) / 2.0 / w
        y_center = (ymin + ymax) / 2.0 / h
        box_w = (xmax - xmin) / w
        box_h = (ymax - ymin) / h

        yolo_lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}")
    return yolo_lines


def save_data(subset, subset_name, xml_dir, img_dir, out_dir, classes):
    images_out = os.path.join(out_dir, "images", subset_name)
    labels_out = os.path.join(out_dir, "labels", subset_name)
    os.makedirs(images_out, exist_ok=True)
    os.makedirs(labels_out, exist_ok=True)

    for xml in tqdm(subset, desc=f"处理{subset_name}集", unit="张"):
        xml_path = os.path.join(xml_dir, xml)
        base_name = os.path.splitext(xml)[0]

        img_path = None
        for ext in [".jpg", ".jpeg", ".png", ".JPG"]:
            candidate = os.path.join(img_dir, base_name + ext)
            if os.path.exists(candidate):
                img_path = candidate
                break
        if not img_path:
            print(f"[跳过] 找不到图像: {base_name}")
            continue

        yolo_lines = convert_voc_to_yolo(xml_path, img_path, classes)
        if not yolo_lines:
            continue

        shutil.copy(img_path, os.path.join(images_out, os.path.basename(img_path)))

        label_file = os.path.join(labels_out, base_name + ".txt")
        with open(label_file, "w") as f:
            f.write("\n".join(yolo_lines))


def generate_data_yaml(out_dir, classes):
    yaml_path = os.path.join(out_dir, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"""train: images/train
val: images/val
test: images/test

nc: {len(classes)}
names: {classes}
""")
    print(f"[✓] data.yaml generated at {yaml_path}")


def main(xml_dir, img_dir, out_dir):
    classes = ['yyzd', 'ygfs', 'zw', 'yyzd_zw', 'ns', 'yyzd_ns', 'zw_ns', 'gfbzjbx', 'gfbqs', 'mbsl', 'snow', 'crack']
    xml_files = [f for f in os.listdir(xml_dir) if f.endswith('.xml')]
    random.shuffle(xml_files)

    total = len(xml_files)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)

    train_images = xml_files[:train_end]
    val_images = xml_files[train_end:val_end]
    test_images = xml_files[val_end:]

    print(f"[*] Found {total} annotated images.")
    print("[*] Saving training set...")
    save_data(train_images, "train", xml_dir, img_dir, out_dir, classes)
    print("[*] Saving validation set...")
    save_data(val_images, "val", xml_dir, img_dir, out_dir, classes)
    print("[*] Saving testing set...")
    save_data(test_images, "test", xml_dir, img_dir, out_dir, classes)

    generate_data_yaml(out_dir, classes)

    print("[✓] Conversion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert VOC XML annotations to YOLO format and split into train/val/test.")
    parser.add_argument("--xml_dir", default="可见光xml", help="Path to directory containing VOC XML annotation files")
    parser.add_argument("--img_dir", default="可见光jpg", help="Path to directory containing image files")
    parser.add_argument("--out_dir", default="可见光_yolo", help="Output directory for YOLO formatted dataset")
    args = parser.parse_args()

    main(args.xml_dir, args.img_dir, args.out_dir)
