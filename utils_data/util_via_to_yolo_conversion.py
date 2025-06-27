import os
import json
import random
import shutil
import argparse
from PIL import Image


def convert_polygon(points, width, height):
    normalized = []
    for x, y in points:
        x_norm = min(max(x / width, 0), 1)
        y_norm = min(max(y / height, 0), 1)
        normalized.extend([x_norm, y_norm])
    return normalized


def load_annotations_from_folder(folder, class_id):
    data = {}
    for fname in os.listdir(folder):
        if not fname.endswith(".json"):
            continue
        json_path = os.path.join(folder, fname)
        with open(json_path, "r", encoding="utf-8") as f:
            ann = json.load(f)
        image_path = os.path.basename(ann["imagePath"]).replace("\\", "/")
        shapes = ann.get("shapes", [])
        polygons = []
        for shape in shapes:
            if shape.get("shape_type") != "polygon":
                continue
            polygons.append({
                "label": class_id,
                "points": shape["points"]
            })
        if polygons:
            data[image_path] = data.get(image_path, []) + polygons
    return data


def generate_data_yaml(output_dir, classes):
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"""train: images/train
val: images/val
test: images/test

nc: {len(classes)}
names: {classes}
""")
    print(f"[✓] data.yaml generated at {yaml_path}")


def main(input_dir, output_dir):
    classes = ['component', 'string']
    component_dir = os.path.join(input_dir, "component")
    string_dir = os.path.join(input_dir, "string")
    image_dir = os.path.join(input_dir, "images")

    print("[*] Loading annotations...")

    component_anns = load_annotations_from_folder(component_dir, classes.index('component'))
    string_anns = load_annotations_from_folder(string_dir, classes.index('string'))

    all_data = {}
    all_data.update(component_anns)
    for k, v in string_anns.items():
        all_data[k] = all_data.get(k, []) + v

    print("[*] Merging annotations...")
    all_images = list(all_data.keys())
    random.shuffle(all_images)
    total = len(all_images)
    train_end = int(0.8 * total)
    val_end = int(0.9 * total)
    train_images = all_images[:train_end]
    val_images = all_images[train_end:val_end]
    test_images = all_images[val_end:]

    def save_data(subset, subset_name):
        images_out = os.path.join(output_dir, "images", subset_name)
        labels_out = os.path.join(output_dir, "labels", subset_name)
        os.makedirs(images_out, exist_ok=True)
        os.makedirs(labels_out, exist_ok=True)

        for img_name in subset:
            img_path = os.path.join(image_dir, img_name)
            out_img_path = os.path.join(images_out, img_name)
            shutil.copy(img_path, out_img_path)

            img = Image.open(img_path)
            w, h = img.size

            label_txt = []
            for obj in all_data[img_name]:
                norm_poly = convert_polygon(obj["points"], w, h)
                label_line = f"{obj['label']} " + " ".join(f"{x:.6f}" for x in norm_poly)
                label_txt.append(label_line)

            label_path = os.path.join(labels_out, os.path.splitext(img_name)[0] + ".txt")
            with open(label_path, "w") as f:
                f.write("\n".join(label_txt))

    print(f"[*] Found {len(all_images)} annotated images.")
    print("[*] Saving training set...")
    save_data(train_images, "train")
    print("[*] Saving validation set...")
    save_data(val_images, "val")
    print("[*] Saving testing set...")
    save_data(test_images, "test")

    generate_data_yaml(output_dir, classes)

    print("[✓] Conversion complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert LabelMe-style JSON to YOLOv11 segmentation format")
    parser.add_argument("--input_dir", default="可见光数据集", required=False, help="输入文件夹路径，包含 images/, component/, string/")
    parser.add_argument("--output_dir", default="可见光数据集_yolo", required=False, help="输出的 YOLO 格式数据集目录")
    args = parser.parse_args()

    main(args.input_dir, args.output_dir)
