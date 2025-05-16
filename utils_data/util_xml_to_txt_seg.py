import os
import xml.dom.minidom
from pathlib import Path

# 指定源文件夹路径
source_folder = input("请输入包含 train/test/val 子文件夹的labels文件夹路径：").strip()

# 检查源文件夹是否存在
if not os.path.exists(source_folder):
    print("指定的源文件夹不存在！")
    exit()

# 创建 YOLO 格式标签的存储文件夹（如果不存在）
yolo_labels_folder = os.path.join(source_folder, "yolov5_txt")
os.makedirs(yolo_labels_folder, exist_ok=True)

# 映射类别名称到数字标签
class_mapping = {
    "panel": 0
}

# 定义处理一个 XML 文件的函数
def process_xml(xml_path, txt_path, width, height):
    dom = xml.dom.minidom.parse(xml_path)
    collection = dom.documentElement

    # 如果 XML 中有多个对象，需要处理每一个
    objects = collection.getElementsByTagName("object")
    txt_content = ""

    for obj in objects:
        name = obj.getElementsByTagName("name")[0].childNodes[0].data
        label = class_mapping.get(name)

        if label is None:
            print(f"警告：未识别的类别 '{name}' 在文件 {xml_path}")
            continue

        # 获取多边形点
        polygon = obj.getElementsByTagName("polygon")[0]
        points = []
        for i in range(1, 6):  # 假设最多5个点
            x = int(polygon.getElementsByTagName(f"x{i}")[0].childNodes[0].data)
            y = int(polygon.getElementsByTagName(f"y{i}")[0].childNodes[0].data)
            points.append((x, y))

        # 去除重复的最后一个点
        if len(points) > 1 and points[-1] == points[0]:
            points.pop()

        # 拼接成 YOLO 格式的字符串
        txt_line = f"{label}"
        for point in points:
            txt_line += f" {point[0] / width:.14f} {point[1] / height:.14f}"
        txt_line += "\n"
        txt_content += txt_line

    # 如果有内容，则写入文件
    if txt_content:
        with open(txt_path, 'w') as f:
            f.write(txt_content)
        print(f"转换成功: {xml_path} → {txt_path}")
    else:
        print(f"警告：'{xml_path}' 中没有有效的对象或类别，跳过该文件!")

# 遍历 train, test, val 子文件夹
subfolders = ["train", "test", "val"]

for subfolder in subfolders:
    # 获取子文件夹的完整路径
    current_subfolder = os.path.join(source_folder, subfolder)
    if not os.path.exists(current_subfolder):
        print(f"子文件夹 '{subfolder}' 不存在，跳过")
        continue

    # 遍历子文件夹中的 XML 文件
    for xml_file in Path(current_subfolder).glob("*.xml"):
        # 解析 XML 获取宽度和高度
        dom = xml.dom.minidom.parse(str(xml_file))
        collection = dom.documentElement

        size = collection.getElementsByTagName("size")[0]
        width = int(size.getElementsByTagName("width")[0].childNodes[0].data)
        height = int(size.getElementsByTagName("height")[0].childNodes[0].data)

        # 定义输出的 txt 文件路径
        txt_file = Path(yolo_labels_folder) / subfolder / f"{xml_file.stem}.txt"
        os.makedirs(txt_file.parent, exist_ok=True)  # 创建子文件夹

        # 处理当前 XML 文件
        process_xml(str(xml_file), str(txt_file), width, height)

print("\n所有文件转换完成！")