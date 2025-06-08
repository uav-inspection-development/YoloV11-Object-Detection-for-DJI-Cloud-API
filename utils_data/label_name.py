import os
import xml.etree.ElementTree as ET
from collections import defaultdict


def count_xml_categories(folder_path):
    """
    统计文件夹中所有XML文件的<name>种类
    :param folder_path: XML文件所在的文件夹路径
    :return: 包含所有唯一类别的集合
    """
    category_counter = defaultdict(int)
    unique_categories = set()

    # 遍历文件夹中的所有XML文件
    for filename in os.listdir(folder_path):
        if not filename.endswith('.xml'):
            continue

        file_path = os.path.join(folder_path, filename)
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # 查找所有object标签
            for obj in root.findall('object'):
                name_tag = obj.find('name')
                if name_tag is not None and name_tag.text:
                    category = name_tag.text.strip()
                    unique_categories.add(category)
                    category_counter[category] += 1

        except ET.ParseError as e:
            print(f"解析错误 {filename}: {str(e)}")
        except Exception as e:
            print(f"处理 {filename} 时出错: {str(e)}")

    return unique_categories, category_counter


if __name__ == "__main__":
    # 设置包含XML文件的文件夹路径
    xml_folder = r"E:\project\YoloV11-Object-Detection-for-DJI-Cloud-API\datasets\visiual\可见光xml"

    # 检查文件夹是否存在
    if not os.path.exists(xml_folder):
        print(f"错误: 文件夹不存在 - {xml_folder}")
    else:
        categories, counter = count_xml_categories(xml_folder)

        print("\n找到的类别种类:")
        print("-" * 30)
        for i, cat in enumerate(sorted(categories), 1):
            print(f"{i}. {cat} (出现次数: {counter[cat]})")

        print("-" * 30)
        print(f"总类别数: {len(categories)}")